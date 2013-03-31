import sys,logging,os
from git import *

issueid = ""
startpoint = ""

def usage():
	print "the following commands are valid:"


def create_remote(repo):
	exists = False
	
	gerrit_remote = repo.remote("gerrit_upstream_remote")
	
	for r in repo.remotes:
		if r.name == "gerrit_upstream_remote":
			exists = True
	
	if exists == False:
		repo.create_remote('gerrit_upstream_remote', 'git@github.com:rob-ward/gerrit-flow.git')

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
	
def branch_exist(bname, repo,remote):
	
	found = branch_exist_local(bname, repo)
	
	if found !=  True:
		branch_exist_remote(bname, repo, remote)
		
	return found

def write_config(repo, issueid, key, value):
	writer = repo.config_writer("repository")
	
	sectionname = 'gerrit-flow "' + issueid + '"'
	
	if writer.has_section(sectionname) == False:
		writer.add_section(sectionname)
	
	writer.set(sectionname, key, value)
	
	
def checkout(repo, bname):
	found = False
	for b in repo.branches:
		if str(b) == bname:
			b.checkout()
			return


	

def do_start(argv):

	#start ISSUEID  <origin point>	
	logging.warning("entering :" + str(argv))
	
	
	if len(argv) < 3 or len(argv) > 4:
		#not a valid star command
		print "Invalid command - usage is as follows"
		usage()
	else:
		issueid=argv[2]
		
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
					#creation of branch was succesful
				
					write_config(repo, issueid, "startpoint" , startpoint)
					
					checkout(repo, issueid)
	
			else:
				print " A local branch called " + issueid + " exists!. As such we cannot start a new instance for this issue."
	
		
		
		
		
		
		
			


def do_draft(argv):
	logging.debug("entering")
	print 'Argument List start :', str(argv)
	
def do_push(argv):
	logging.debug("entering")
	print 'Argument List start :', str(argv)
	
def do_rework(argv):
	logging.debug("entering")
	print 'Argument List start :', str(argv)
	
def do_suck(argv):
	logging.debug("entering")
	print 'Argument List start :', str(argv)

def do_review(argv):
	logging.debug("entering")
	print 'Argument List ',  str(argv)

dispatch = {
	'start': 	do_start,
	'draft':	do_draft,
	'push': 	do_push,
	'rework': 	do_rework,
	'suck': 	do_suck,
	'review': 	do_review,
		
}


def main():


	print 'Number of arguments:', len(sys.argv), 'arguments.'


	if sys.argv[1] in dispatch:
		dispatch[sys.argv[1]](sys.argv)
	else:
		print "nothin"


if __name__ == "__main__":
	logging.basicConfig(format="%(asctime)s: - %(filename)s: - %(funcName)s:%(message)s",level=logging.DEBUG,stream=sys.stdout)
	main()
