#! /usr/bin/env python

import sys, logging, os, subprocess, hashlib, json
from git import *



def usage():
	print "the following commands are valid:"

def get_origin_url():
	origin_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).rstrip()
	return origin_url

def get_server_hostname(url):
	start = url.find("@")
	url = url[start + 1:]
	end = url.find(":")
	hostname = url[:end]
	return hostname

def get_server_port(url):
	start = url.find(":")
	url = url[start + 1:]
	start = url.find(":")
	url = url[start + 1:]
	end = url.find("/")
	port = url[:end]
	return port

def create_remote(repo):
	exists = False
	
	
	for r in repo.remotes:
		if r.name == "gerrit_upstream_remote":
			exists = True
	
	if exists == False:
		origin_url = get_origin_url()
		repo.create_remote('gerrit_upstream_remote', origin_url)

	repo.remote("gerrit_upstream_remote").fetch() 
	
	return repo.remote("gerrit_upstream_remote")
	
def branch_exist_local(bname, repo):
	found = False
	for b in repo.branches:
		if str(b) == bname:
			found = True
	
	return found;
	
def branch_exist_remote(bname, repo, remote):
	found = False
	for r in remote.refs:
		if str(r) == "gerrit_upstream_remote/" + bname:
			found = True
	
	return found;
	
def branch_exist(bname, repo, remote):
	
	found = branch_exist_local(bname, repo)
	
	if found != True:
		branch_exist_remote(bname, repo, remote)
		
	return found

def write_config(repo, issueid, key, value):
	writer = repo.config_writer("repository")
	
	sectionname = 'gerrit-flow "' + issueid + '"'
	
	if writer.has_section(sectionname) == False:
		writer.add_section(sectionname)
	
	writer.set(sectionname, key, value)
	
def read_config(repo, issueid, key):
	reader = repo.config_reader("repository")
	
	sectionname = 'gerrit-flow "' + issueid + '"'
	
	value = reader.get(sectionname, key)
	
	return value
	
def checkout(repo, bname):
# need to check if there are modified files, if there are fail
	for b in repo.branches:
		if str(b) == bname:
			b.checkout()
			return True
		
	return False

def do_start(argv):

	# start ISSUEID  <origin point>	
	logging.warning("entering :" + str(argv))
	
	
	if len(argv) < 3 or len(argv) > 4:
		# not a valid star command
		print "Invalid command - usage is as follows"
		usage()
	else:
		issueid = argv[2]
		
		global startpoint
		
		if len(argv) == 4:
			startpoint = argv[3]
		else:
			startpoint = "master"
	
		repo = Repo(os.getcwd())
		remote = create_remote(repo)
		
		if branch_exist_remote(startpoint, repo, remote) == False:
			print "The requested startpoint cannot be found on the gerrit server, you must specify a branch which exists upstream(where you changes will be merged back onto)"
		else:
			if branch_exist(issueid, repo, remote) == False:
				repo.git.branch(issueid, 'gerrit_upstream_remote/' + startpoint)
				if branch_exist_local(issueid, repo) == True:
					# creation of branch was succesful
				
					write_config(repo, issueid, "startpoint" , startpoint)
					
					checkout(repo, issueid)
	
			else:
				print " A local branch called " + issueid + " exists!. As such we cannot start a new instance for this issue."
	
		
def submit(repo, ref, append):
	remote = create_remote(repo)
		
	issueid = repo.active_branch
		
	print issueid
	startpoint = read_config(repo, issueid.name, "startpoint")
		
	# Check that the branch doesn't exist, then create it
	if branch_exist(issueid.name + append, repo, remote) == True:
		print "PANIC Stations:\n\tThe branch for this change commit already exists, this\n\tlikely means that a" + \
			" previous draft upload\n\tfailed, the branch called " + issueid.name + append + \
			" must be\n\tremoved before you can continue."
	else:
			retval = repo.git.branch(issueid.name + append, 'gerrit_upstream_remote/' + startpoint)
			print retval
			retval = checkout(repo, issueid.name + append)
			print retval
			try:
				retval = repo.git.merge("--squash", "--no-commit", issueid)
			except:
				print "Oh Dear:\n\tThe merge into the latest tip of " + startpoint + " failed." + \
						"\n\tThe likely hood is that you need to merge in the latest changes in " + startpoint + \
						"\n\tinto your branch"
				repo.git.reset("--hard", "HEAD")
				issueid.checkout()
				repo.git.branch("-D", issueid.name + append)
				return
		
			commithash = hashlib.new('ripemd160')
			commithash.update(issueid.name)
			
			url = get_origin_url()
			hostname = get_server_hostname(url)
			port = get_server_port(url)
			
			print "url = " + url + "    host =" + hostname + "    port = " + port

			
			
			commitmessage = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "change:I" + commithash.hexdigest() ])
			if commitmessage.find("rowCount: 0") >= 0:
				# we don't have so a commit message
				commitmessage = issueid.name + " - \n# Brief summary on line above(<50 chars)\n\n" + \
					"# Describe in detail the change below\nChange-Description:\n\n\n# Describe how to test your change below\n" + \
				 	"Change-TestProcedure:\n\n\n# DO NOT EDIT ANYTHING BELOW HERE\n\nGerrit.startpoint:" + startpoint + \
				 	"\n\nChange-Id:I" + commithash.hexdigest()
			else:
				# we have a commit message be we have to paarse if from json
				print commitmessage
				start = commitmessage.find(',"commitMessage":"')
				start = start + 18
				
				end = commitmessage.find('","createdOn":')
				commitmessage = commitmessage[start:end].replace("\\n", "\n")
				print commitmessage
				commitmessage = commitmessage.replace("Gerrit.startpoint:", "# DO NOT EDIT ANYTHING BELOW HERE\n\nGerrit.startpoint:")
								
			f = open(issueid.name + '_commitmessage', 'w')
			f.write(commitmessage)
			f.close()
							
				
			subprocess.call(['vim', issueid.name + '_commitmessage'])
			commitmessage = "" 
			
			f = file(issueid.name + '_commitmessage', "r")
			for line in f:
				if not line.startswith("#"):
					commitmessage = commitmessage + line
	
			
			repo.git.commit("-a", '-m', commitmessage)
			try:
				retval = subprocess.check_output(["git", "push", "gerrit_upstream_remote", ref + startpoint], stderr=subprocess.STDOUT)
			except subprocess.CalledProcessError as e:
				retval = e.output
			
			print "ret = "
			print retval.find("(no changes made)")
			if retval.find("(no changes made)") >= 0:
				print "Oh Dear: \n\tYou don't seem to have commited any changes, make\n\tsure you have saved your files, and committed them!!"
			
			issueid.checkout()
			repo.git.branch("-D", issueid.name + append)
				

def do_draft(argv):
	print 'Argument List start :', str(argv)
	if len(argv) != 2:
		# not a valid star command
		print "Invalid command - usage is as follows"
		usage()
	else:
		repo = Repo(os.getcwd())
		submit(repo, "HEAD:refs/drafts/", "_draft")
		
		
		
	
	
def do_push(argv):
	print 'Argument List start :', str(argv)
	if len(argv) != 2:
		# not a valid star command
		print "Invalid command - usage is as follows"
		usage()
	else:
		repo = Repo(os.getcwd())
		submit(repo, "HEAD:refs/for/", "_push")
		
		
	
def do_rework(argv):
	logging.debug("entering")
	print 'Argument List start :', str(argv)
	
def do_suck(argv):
	logging.debug("entering")
	print 'Argument List start :', str(argv)

def do_review(argv):
	logging.debug("entering")
	print 'Argument List ', str(argv)

dispatch = {
	'start': 	do_start,
	'draft':	do_draft,
	'push': 	do_push,
	'rework': 	do_rework,
	'suck': 	do_suck,
	'review': 	do_review,
		
}


def main():

	print os.getcwd()
	

	print 'Number of arguments:', len(sys.argv), 'arguments.'


	if sys.argv[1] in dispatch:
		dispatch[sys.argv[1]](sys.argv)
	else:
		print "nothin"


if __name__ == "__main__":
	logging.basicConfig(format="%(asctime)s: - %(filename)s: - %(funcName)s:%(message)s", level=logging.DEBUG, stream=sys.stdout)
	main()
