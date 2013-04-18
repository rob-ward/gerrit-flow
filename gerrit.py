#! /usr/bin/env python

import sys, logging, os, subprocess, hashlib, json, datetime, webbrowser
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
		return
	
	repo = Repo(os.getcwd())
	
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		return
	
	issueid = argv[2]
		
	global startpoint
		
	if len(argv) == 4:
		startpoint = argv[3]
	else:
		startpoint = "master"

	
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
			
			commitmessage = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "change:I" + commithash.hexdigest() ])
			if commitmessage.find('"rowCount":0') >= 0:
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
		return
	
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		return
	
	repo = Repo(os.getcwd())
	submit(repo, "HEAD:refs/drafts/", "_draft")
		
		
		
	
	
def do_push(argv):
	print 'Argument List start :', str(argv)
	if len(argv) != 2:
		# not a valid star command
		print "Invalid command - usage is as follows"
		usage()
		return
	
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		return

	submit(repo, "HEAD:refs/for/", "_push")
		
		
def clone_ref(issue_name, repo):
	print "clone_ref - " + issue_name
	commithash = hashlib.new('ripemd160')
	commithash.update(issue_name)
	
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
			
	commitmessage = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--current-patch-set", "change:I" + commithash.hexdigest() ])
	if commitmessage.find('"rowCount":0') >= 0:
		# we don't have so a commit message
		print "Oh Dear:\n\tThe issue name you provided doesn't seem to exist on\n\tthe server(" + hostname + "), check you know how to type and\n\tthe change is on the server."
		return ""
	else:
		create_remote(repo)
		start = commitmessage.find('"ref":"')
		start = start + 7
		end = commitmessage.find('","uploader"')
		ref = commitmessage[start:end]
		print ref
		repo.git.fetch("gerrit_upstream_remote", ref)
		repo.git.checkout("FETCH_HEAD")
		return ref

def do_rework(argv):
	if len(argv) < 3 or len(argv) > 4 :
		# not a valid star command
		print "Invalid command - usage is as follows"
		usage()
		return
	
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		return
	
	issue_name = argv[2]
	mergechanges = False
	if len(argv) == 4:
		if argv[3] == "merge":
			mergechanges = True
		
	ref = clone_ref(issue_name, repo)
	if ref != "":
		# we have a ref
		if branch_exist_local(issue_name, repo) == False:
			if mergechanges == False:
				repo.git.checkout("-b", issue_name)
				if(repo.active_branch.name != issue_name):
					print "Oh Dear:\n\tCheckout of the new branch failed. Please clean the git repo and try again!"
				else:
					print "You are now on branch " + issue_name
					
				commithash = hashlib.new('ripemd160')
				commithash.update(issue_name)
	
				url = get_origin_url()
				hostname = get_server_hostname(url)
				port = get_server_port(url)
			
				commitmessage = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "change:I" + commithash.hexdigest() ])
				
				print "commitmesage1 =" + commitmessage
				start = commitmessage.find(',"commitMessage":"')
				start = start + 18
				
				
				end = commitmessage.find('","createdOn":')
				commitmessage = commitmessage[start:end].replace("\\n", "\n")
				startpoint = "master"
				for line in commitmessage.split('\n'):
					if line.find("Gerrit.startpoint:") != -1:
						startpoint = line.split(':')[1]

				write_config(repo, issue_name, "startpoint" , startpoint)
			else:
				print "Oh Dear: You have requested a merge but the branch doesn't currently exist locally."
		else:
			# brnach exists
			if mergechanges == False:
				print "Oh Dear:\n\tIt appears that the creation of the new branch " + issue_name + " can't \n\thappen " + \
				"due to a branch with this name already existing. If you want to" + \
				"\n\tmerge the changes onto that branch then run git gerrit rework ISSUEID merge" + \
				"\n\tPlease remove this branch and try again!"
			else:
				repo.git.checkout(issue_name)
				if(repo.active_branch.name != issue_name):
					print "Oh Dear:\n\tCheckout of the existing branch failed, please check that you have a clean git repo"
				else:
					print "You are now on branch " + issue_name
					
				try:
					repo.git.pull("gerrit_upstream_remote", ref)
				except GitCommandError as e:
					if e.status == 1:
						print "Oh Dear:\n\tIt appears that the automerge failed, please use\n\t git mergetool to complete the action and then perform a commit"
							
				
			
				
	
def do_suck(argv):
	if len(argv) != 3 :
		# not a valid star command
		print "Invalid command - usage is as follows"
		usage()
		return
	
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		return
	
	issue_name = argv[2]
	if branch_exist_local(issue_name, repo) == False:
		clone_ref(issue_name, repo,)
		try:
			repo.git.checkout("-b", issue_name + "_suck")
		except:
			print "Oh Dear:\n\tIt appears that the creation of the new branch " + issue_name + "_suck has\n\tfailed. Please check you git repo and try again."
	else:
		print "Oh Dear:\n\tIt appears that the creation of the new branch " + issue_name + "_suck can't \n\thappen" + \
				"due to a branch with this name already existing. If you want to" + \
				"\n\tmerge the changes onto that branch then run git gerrit rework ISSUEID merge" + \
				"\n\tPlease remove this branch and try again!"

def review_summary(issue_name):
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = hashlib.new('ripemd160')
	commithash.update(issue_name)
				
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "--current-patch-set", "change:I" + commithash.hexdigest() ])
	# info.replace("id: I", "Change ID: I")
	decoded = json.loads(info.splitlines()[0])
	
	project = decoded['project']
	branch = decoded['branch']
	owner = decoded['owner']['name']
	owner_email = decoded['owner']['email']
	status = decoded['status']
	created = datetime.datetime.fromtimestamp(decoded['createdOn']).strftime('%d-%m-%Y %H:%M:%S')
	updated = datetime.datetime.fromtimestamp(decoded['lastUpdated']).strftime('%d-%m-%Y %H:%M:%S')
	commitmessage = decoded['commitMessage']
	numberofpatches = decoded['currentPatchSet']['number']
	uri = decoded['url']
	
	
	print "Project : " + project
	print "Branch : " + branch
	print "Change Owner : " + owner + " - " + owner_email
	print "\nStatus : " + status
	print "\nCreated on : " + created
	print "Updated On : " + updated
	print "Commit message: "
	for l in commitmessage.splitlines():
		print "\t\t" + l
	
	print "\nNumber of Patchsets : " + str(numberofpatches)
	print "Change URI : " + uri
	
def review_web(issue_name):
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = hashlib.new('ripemd160')
	commithash.update(issue_name)
				
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "--current-patch-set", "change:I" + commithash.hexdigest() ])
	decoded = json.loads(info.splitlines()[0])
	uri = decoded['url']
	try:
		webbrowser.open(uri)
	except:
		print "Oh Dear:\n\tIt appears that we can't open a browser or that the uri we have is invalid. Try visiting: " + uri

def review_patch(issue_name):
	repo = Repo(os.getcwd())

	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = hashlib.new('ripemd160')
	commithash.update(issue_name)
				
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--current-patch-set", "change:I" + commithash.hexdigest() ])
	decoded = json.loads(info.splitlines()[0])
	
	ref = decoded['currentPatchSet']['ref']
	repo.git.fetch(url, ref)
	patch = subprocess.check_output(['git', "format-patch", "-1", "--stdout", "FETCH_HEAD" ])
	print patch
	



def review_tool(issue_name):
	print "review_tool"
	
summary_type = {
	'web': 		review_web,
	'summary':	review_summary,
	'patch': 	review_patch,
	'tool': 	review_tool,
}


def do_review(argv):
	if len(argv) < 3 or len(argv) > 4 :
		# not a valid star command
		print "Invalid command - usage is as follows"
		usage()
		return
	
	stype = "web"
	
	issue_name = argv[2]
	if len(argv) == 4:
		stype = argv[3]
		
	if stype in summary_type:
		summary_type[stype](issue_name)
	else:
		print "Oh Dear:\n\tThis is not a valid review type. Check for a type!! \n\n\tIf you would like a new type adding let us know!"

def do_cherrypick(argv):
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		return
	
	if len(argv) != 3:
		print "Oh Dear:\n\tCherrypick only supports a command with a issue name after it, please try again!"
		return
	
	issue_name = argv[2]
	
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = hashlib.new('ripemd160')
	commithash.update(issue_name)
				
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--current-patch-set", "change:I" + commithash.hexdigest() ])
	decoded = json.loads(info.splitlines()[0])
	
	ref = decoded['currentPatchSet']['ref']
	repo.git.fetch(url, ref)
	repo.git.cherry_pick("FETCH_HEAD")
	
	


dispatch = {
	'start': 		do_start,
	'draft':		do_draft,
	'push': 		do_push,
	'rework': 		do_rework,
	'suck': 		do_suck,
	'review': 		do_review,
	'cherrypick': 	do_cherrypick,
	'cherry-pick': 	do_cherrypick,
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
