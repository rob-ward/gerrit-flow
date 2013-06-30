#! /usr/bin/env python

# Copyright (c) 2013, Rob Ward
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
#
#    Redistributions of source code must retain the above copyright
# 	 notice, this list of conditions and the following disclaimer.
#
# 	 Redistributions in binary form must reproduce the above copyright 
#    notice, this list of conditions and the following disclaimer in
# 	 the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.


# gerrit-flow -- Is a set of functionality to support interaction with
# the gerrit code review tool (http://code.google.com/p/gerrit/)
#
# This tool supports interaction with the gerrit server in a way that
# allows a number of workflows to be used in development.
# 
# Please report any bugs to or feature requests to;
# 			https://github.com/rob-ward/gerrit-flow
#


 
import sys
import os
import logging 
import subprocess 
import hashlib
import json
import datetime 
import webbrowser 
import random
from git import *


global GERRIT_FLOW_VERSION
GERRIT_FLOW_VERSION = "0.0.1"
#############################

def get_origin_url():
	logging.info("entering")
	origin_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).rstrip()
	logging.info("origin_url = " + origin_url)
	return origin_url

#############################

def get_server_hostname(url):
	logging.info("entering")
	start = url.find("@")
	if start == -1:
		#we need to handle urls without a username
		start = url.find(":")
		start = start + 2 # miss the //

	url = url[start + 1:]
	end = url.find(":")
	hostname = url[:end]
	logging.info("hostname = " + hostname)
	return hostname

#############################

def get_server_port(url):
	logging.info("entering")
	start = url.find(":")
	url = url[start + 1:]
	start = url.find(":")
	url = url[start + 1:]
	end = url.find("/")
	port = url[:end]
	logging.info("port = " + port)
	return port

#############################

def create_remote(repo):
	logging.info("entering")
	exists = False
	
	for r in repo.remotes:
		if r.name == "gerrit_upstream_remote":
			exists = True
			logging.info("repo already exists")
	
	if exists == False:
		origin_url = get_origin_url()
		logging.info("create new remote")
		repo.create_remote('gerrit_upstream_remote', origin_url)

	logging.info("fetching from remote")
	repo.remote("gerrit_upstream_remote").fetch() 
	
	return repo.remote("gerrit_upstream_remote")

#############################

def branch_exist_local(bname, repo):
	logging.info("entering")
	found = False
	for b in repo.branches:
		if str(b) == bname:
			found = True
			logging.info("branch exists local")
	
	
	return found;

#############################
	
def branch_exist_remote(bname, repo, remote):
	logging.info("entering")
	found = False
	for r in remote.refs:
		if str(r) == "gerrit_upstream_remote/" + bname:
			found = True
			logging.info("branch exists remote")
	
	return found;

#############################

def branch_exist(bname, repo, remote):
	logging.info("entering")
	
	found = branch_exist_local(bname, repo)
	
	if found != True:
		found = branch_exist_remote(bname, repo, remote)
		
	if found == True:
		logging.info("Branch exists")
	else:
		logging.info("Branch DOES NOT exist")
		
	return found

#############################

def write_config(repo, issueid, key, value):
	logging.info("entering")
	
	logging.info("paramaters[repo, issueid = " + issueid + ", key = " + key + ", value = " + value + "]")
	writer = repo.config_writer("repository")
	
	sectionname = 'gerrit-flow "' + issueid + '"'
	logging.info("section name = " + sectionname)
	if writer.has_section(sectionname) == False:
		logging.info("writer doesn't have section")
		writer.add_section(sectionname)
	
	writer.set(sectionname, key, value)
	
#############################	
	
def read_config(repo, issueid, key):
	logging.info("entering")	
	logging.info("paramaters[repo, issueid = " + issueid + ", key = " + key + "]")
	reader = repo.config_reader("repository")
	
	sectionname = 'gerrit-flow "' + issueid + '"'
	logging.info("section name = " + sectionname)
	
	value = reader.get(sectionname, key)
	logging.info("value = " + value)
	
	return value

#############################

def get_commit_hash(issue_name):
	logging.info("entering")
	
	logging.info("Issue name =" + issue_name)
		
	commithash = hashlib.sha1()
	commithash.update(issue_name)
	
	logging.info("Commit Hash = I" + commithash.hexdigest())
	
	return commithash.hexdigest()

#############################

def issue_exists_on_server(issue_name):
	logging.info("entering")

	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = get_commit_hash(issue_name)
	
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--current-patch-set", "change:I" + commithash ])
	if len(info.splitlines()) > 1:
		logging.info("Issue exists")
		return True
	else:
		logging.info("Issue DOES NOT exist")
		return False
	
#############################

def checkout(repo, bname):
	logging.info("entering")
		
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.info("Dirty repo")
		return False

# need to check if there are modified files, if there are fail
	for b in repo.branches:
		if str(b) == bname:
			logging.info("found branch")
			b.checkout()
			return True
		
	return False

#############################

def do_start(argv):
	logging.info("entering")

	# start ISSUEID  <origin point>	
	
	
	if len(argv) < 3 or len(argv) > 4:
		# not a valid star command
		print "Invalid command parameters"
		logging.info("Bad parameters")
		return
	
	repo = Repo(os.getcwd())
	
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.info("Repor dirty")
		return
	
	issueid = argv[2]
		
	startpoint = "master"
		
	if len(argv) == 4:
		startpoint = argv[3]

	logging.info("Startpoint is " + startpoint)

	
	remote = create_remote(repo)
	
	if branch_exist_remote(startpoint, repo, remote) == False:
		print "Oh Dear:\n\tThe requested startpoint cannot be found on the gerrit server, you must" + \
		"\tspecify a branch which exists upstream(where you changes will be merged back onto)"
		logging.info("Startpoint not on server")
	else:
		if branch_exist(issueid, repo, remote) == False:
			logging.info("No branch called " + issueid + " exists")
			repo.git.branch(issueid, 'gerrit_upstream_remote/' + startpoint)
			if branch_exist_local(issueid, repo) == True:
				# creation of branch was succesful
				write_config(repo, issueid, "startpoint" , startpoint)
				checkout(repo, issueid)
				print("You are now checkedout on " + issueid)
				logging.info("Branch creation was succesful")
			else:
				logging.info("Branch creation Failed")

		else:
			print "Oh Dear:\n\tA local branch called " + issueid + " exists!.\n\tAs such we cannot start a new instance for this issue."
			logging.info("Local branch already exists")

#############################

def submit(repo, ref, append):
	logging.info("entering")
	remote = create_remote(repo)
		
	issueid = repo.active_branch
		
	startpoint = read_config(repo, issueid.name, "startpoint")
	logging.info("Startpoint = " + startpoint)
	# Check that the branch doesn't exist, then create it
	if branch_exist(issueid.name + append, repo, remote) == True:
		print "PANIC Stations:\n\tThe branch for this change commit already exists, this\n\tlikely means that a" + \
			" previous draft upload\n\tfailed, the branch called " + issueid.name + append + \
			" must be\n\tremoved before you can continue."
		logging.debug("Submit Branch already exits, this is bad")
	else:
			failed = False
			retval = repo.git.branch(issueid.name + append, 'gerrit_upstream_remote/' + startpoint)
			print "\nCreating patchset for submition... Please Standby...\n"
			retval = checkout(repo, issueid.name + append)
			try:
				retval = repo.git.merge("--squash", "--no-commit", issueid)
			except:
				print "Oh Dear:\n\tThe merge into the latest tip of " + startpoint + " failed." + \
						"\n\tThe likely hood is that you need to merge in the latest changes in " + startpoint + \
						"\n\tinto your branch"
				logging.info("Merge into latest tip of startpoint failed")
				logging.info("Reset head --hard")
				repo.git.reset("--hard", "HEAD")
				issueid.checkout()
				logging.info("Deleting branch " + issueid.name + append)
				repo.git.branch("-D", issueid.name + append)
				return
		
			commithash = get_commit_hash(issueid.name)
			
			url = get_origin_url()
			hostname = get_server_hostname(url)
			port = get_server_port(url)
			
			print"\n\nContacting server to confirm that no current commit amssage is present, Standby..."
			
			commitmessage = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "change:I" + commithash ])
			if commitmessage.find('"rowCount":0') >= 0:
				print "\nGenerating default commit message."
				# we don't have so a commit message
				logging.info("No commit message exists so making one")
				commitmessage = issueid.name + " - \n# Brief summary on line above(<50 chars)\n\n\n" + \
					"# Describe in detail the change below\nChange-Description:\n\n\n# Describe how to test your change below\n" + \
				 	"Change-TestProcedure:\n\n\n# DO NOT EDIT ANYTHING BELOW HERE\n\nGerrit.startpoint:" + startpoint + \
				 	"\n\nChange-Id:I" + commithash
			else:
				# we have a commit message be we have to parse if from json
				#todo why is this not in proper json????
				logging.info("We have a commit message")
				start = commitmessage.find(',"commitMessage":"')
				start = start + 18
				
				end = commitmessage.find('","createdOn":')
				commitmessage = commitmessage[start:end].replace("\\n", "\n")
				commitmessage = commitmessage.replace("Gerrit.startpoint:", "# DO NOT EDIT ANYTHING BELOW HERE\n\nGerrit.startpoint:")
			
			logging.info("Writing commit message")
			f = open(issueid.name + '_commitmessage', 'w')
			f.write(commitmessage)
			f.close()
							
				
			subprocess.call(['vim', issueid.name + '_commitmessage'])
			commitmessage = "" 
			
			f = file(issueid.name + '_commitmessage', "r")
			for line in f:
				if not line.startswith("#"):
					commitmessage = commitmessage + line
	
			print "Commiting you change to local git history"
			repo.git.commit("-a", '-m', commitmessage)
			try:
				print "Attempting to push change to the gerrit server, Please Standby...
				retval = subprocess.check_output(["git", "push", "gerrit_upstream_remote", ref + startpoint], stderr=subprocess.STDOUT)
			except subprocess.CalledProcessError as e:
				retval = e.output
			
			#we want the output so print
			print retval

			if retval.find("(no changes made)") >= 0:
				logging.info("o cahnges made")
				print "Oh Dear: \n\tYou don't seem to have commited any changes, make\n\tsure you have saved your files, and committed them!!"
				failed = True
			issueid.checkout()
			logging.info("Checked out original branch")
			logging.info("Deleting branch " + issueid.name + append)
			repo.git.branch("-D", issueid.name + append)
			if failed == False:
				print "Successfully pushed to Gerrit server"
			
#############################

def do_draft(argv):
	logging.info("entering")
	if len(argv) != 2:
		# not a valid star command
		print "Invalid command syntax, please try again"
		logging.info("Invalid command parameters")
		return
	
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.info("Repo is dirty")
		return
	
	repo = Repo(os.getcwd())
	submit(repo, "HEAD:refs/drafts/", "_draft")
		
#############################
	
def do_push(argv):
	logging.info("entering")
	if len(argv) != 2:
		# not a valid star command
		print "Invalid command syntax, please try again"
		logging.info("Invalid command parameters")
		return
	
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.info("Repo is dirty")
		return

	submit(repo, "HEAD:refs/for/", "_push")

#############################	
		
def clone_ref(issue_name, repo):
	logging.info("entering")
	
	commithash = get_commit_hash(issue_name)
	
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
			
	commitmessage = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--current-patch-set", "change:I" + commithash ])
	# TODO use issue_exists_on_server function?
	if commitmessage.find('"rowCount":0') >= 0:
		# we don't have so a commit message
		print "Oh Dear:\n\tThe issue name you provided doesn't seem to exist on\n\tthe server(" + hostname + "), check you know how to type and\n\tthe change is on the server."
		logging.info("Issue doesn't exist on server")
		return ""
	else:
		# TODO use JSON properly
		create_remote(repo)
		start = commitmessage.find('"ref":"')
		start = start + 7
		end = commitmessage.find('","uploader"')
		ref = commitmessage[start:end]
		repo.git.fetch("gerrit_upstream_remote", ref)
		repo.git.checkout("FETCH_HEAD")
		logging.info("returning ref = " + ref)
		return ref

#############################

def do_rework(argv):
	logging.info("entering")
	
	if len(argv) < 3 or len(argv) > 4 :
		# not a valid star command
		print "Invalid command"
		logging.warning("Invalid command options")
		return
	
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.warning("Dirty repo")
		return
	
	issue_name = argv[2]
	logging.info("issue anme = " + issue_name)
	
	mergechanges = False
	if len(argv) == 4:
		if argv[3] == "merge":
			mergechanges = True
			logging.info("Merge changes selected")
		
	ref = clone_ref(issue_name, repo)
	if ref != "":
		# we have a ref
		if branch_exist_local(issue_name, repo) == False:
			if mergechanges == False:
				repo.git.checkout("-b", issue_name)
				logging.info("checkout -b " + issue_name)
				if(repo.active_branch.name != issue_name):
					print "Oh Dear:\n\tCheckout of the new branch failed. Please clean the git repo and try again!"
					logging.info("Failed to checkout branch " + issue_name)
				else:
					print "You are now on branch " + issue_name
					logging.info("Checked out " + issue_name)
								
				commithash = get_commit_hash(issue_name)
	
				url = get_origin_url()
				hostname = get_server_hostname(url)
				port = get_server_port(url)
			
				commitmessage = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "change:I" + commithash ])
				
				# TODO This should be parsed from json, not from string
				start = commitmessage.find(',"commitMessage":"')
				start = start + 18
				
				
				end = commitmessage.find('","createdOn":')
				commitmessage = commitmessage[start:end].replace("\\n", "\n")
				startpoint = "master"
				for line in commitmessage.split('\n'):
					if line.find("Gerrit.startpoint:") != -1:
						startpoint = line.split(':')[1]
						logging.info("Startpoint = " + startpoint)
						
				write_config(repo, issue_name, "startpoint" , startpoint)
			else:
				print "Oh Dear: You have requested a merge but the branch doesn't currently exist locally."
				logging.info("Merge requested but branch doesn't exist")
		else:
			# branch exists
			if mergechanges == False:
				print "Oh Dear:\n\tIt appears that the creation of the new branch " + issue_name + " can't \n\thappen " + \
				"due to a branch with this name already existing. If you want to" + \
				"\n\tmerge the changes onto that branch then run git gerrit rework ISSUEID merge" + \
				"\n\tPlease remove this branch and try again!"
				logging.info("Branch name seems to exist so can't create")
			else:
				logging.info("checkout " + issue_name)
				repo.git.checkout(issue_name)
				if(repo.active_branch.name != issue_name):
					logging.info("Failed to chechout branch " + issue_name)
					print "Oh Dear:\n\tCheckout of the existing branch failed, please check that you have a clean git repo"
				else:
					print "You are now on branch " + issue_name
					logging.info("Checked out " + issue_name)
					
				try:
					logging.info("pulling gerrit remote with ref = " + ref)
					repo.git.pull("gerrit_upstream_remote", ref)
					
				except GitCommandError as e:
					if e.status == 1:
						print "Oh Dear:\n\tIt appears that the automerge into " + startpoint + " failed, please use\n\t git mergetool to complete the action and then perform a commit."
						logging.info("automerge failed")
					else:
						logging.warning("pull failed, big issue")
				
################################					
	
def do_suck(argv):
	logging.info("entering")
	if len(argv) != 3 :
		# not a valid star command
		print "Invalid command options, please read the docs"
		logging.info("Invalid command options")
		return
	
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.info("Repo is dirty")
		return
	
	issue_name = argv[2]
	if branch_exist_local(issue_name, repo) == False:
		clone_ref(issue_name, repo,)
		try:
			logging.info("checkout -b" + issue_name + "_suck")
			repo.git.checkout("-b", issue_name + "_suck")
			print "You are now on branch" + issue_name + "_suck, please delete when done"
		except:
			print "Oh Dear:\n\tIt appears that the creation of the new branch " + issue_name + "_suck has\n\tfailed. Please check you git repo and try again."
			logging.info("Creation of branch " + issue_name + "_suck failed")
	else:
		print "Oh Dear:\n\tIt appears that the creation of the new branch " + issue_name + "_suck can't \n\thappen" + \
				"due to a branch with this name already existing. If you want to" + \
				"\n\tmerge the changes onto that branch then run git gerrit rework ISSUEID merge" + \
				"\n\tPlease remove this branch and try again!"
		logging.info("branch called " + issue_name + "_suck already exists")


#############################	

def do_share(argv):
	logging.info("entering")
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.warning("Repo Dirty")
		return
	
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)

	issueid = repo.active_branch
	
	remote = create_remote(repo)
  
	share_name = "share/" + issueid.name

	# we need to check that we aren't on a share branch, we don't want share/share/share....
	if issueid.name[:6] == "share/":
		print "Oh Dear:\n\tIt appears that the branch you are on is already a share!!"
		logging.warning("Share - " + share_name + " is already a share")
		return
				
	#Check that share/<ISSUEID> doesn't exists, if it does error as we can't have two
	if branch_exist(share_name, repo, remote) == True:
		print "Oh Dear:\n\tShare " + share_name + " already exists"
		logging.warning("Share - " + share_name + " already exists")
		return

	#Move the branch to a share version
	repo.git.branch("-m", issueid, share_name)
	repo.git.push("origin", share_name)

	try:
		retval =  subprocess.check_output(["git", "push", "gerrit_upstream_remote", share_name], stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError as e:
		retval = e.output

	print retval
	
#############################	

def do_scrunch(argv):
	logging.info("entering")
	repo = Repo(os.getcwd())

	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.warning("Repo Dirty")
		return

	
	if len(argv) != 4:
		print "Oh Dear:\n\tScrunch only supports a command with a branch in the form share/ISSUEID and a merge to branch " + \
      "after it, please see help for more info!"
		logging.warning("Scrunch - didn't provide branch from and branch to")
		return

	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
	
	branch_from = argv[2]
	branch_to = argv[3]

	branch_issuename = branch_from[6:]

	remote = create_remote(repo)
  
	#We take files to merge from the server so it must exist
	if branch_exist_remote(branch_from, repo, remote) == False:
		print "Oh Dear:\n\tBranch " + branch_from + " does not exist on the gerrit server, we will only merge from the server!!!"
		logging.warning("Branch " + branch_from + " does not exist on server for scrunching")
		return

	print "Using branch " + branch_from + " from server"

	if branch_exist_local(branch_issuename, repo) == True:
		print "Oh Dear:\n\tA local branch called " + branch_issuename + " exists, we cannot scrunch while it exists!"
		logging.warning("Branch " + branch_issuename + " exist locally")
		return

   
	if issue_exists_on_server(branch_issuename) == True:
		print "Oh Dear:\n\tThe issue " + branch_issuename + " appears to exist on the server already, I don't know what you are doing but be careful!"
		logging.warning("Issue " + branch_issuename + " exist already")
		return

	if branch_exist_remote(branch_to, repo, remote) == False:
		print "Oh Dear:\n\tThe branch you want to merge to - " + branch_to + " - doesn't appears to exist on the server - Aborting!"
		logging.warning("Branch " + branch_to + " doesn't exist on the server")
		return

	repo.git.branch(branch_issuename, 'gerrit_upstream_remote/' + branch_to)

	if branch_exist_local(branch_issuename, repo) == False:
		print "Oh Dear:\n\tThe creation of the branch " + branch_issuename + " failed - Aborting!"
		logging.info("The creation of the branch " + branch_issuename + " failed")
		return

	write_config(repo, branch_issuename, "startpoint" , branch_to)
	checkout(repo, branch_issuename)

	try:
		retval = repo.git.merge("--squash", "--no-commit", branch_from)
	except:
		print "Oh Dear:\n\tThe merge into the latest tip of " + branch_to + " failed." + \
						"\n\tThe likely hood is that you need to merge in the latest changes in " + branch_to + \
						"\n\tinto your branch or deal with the merge conflicts using git mergetool \n\n\tYou " + \
						"are in an unclean state"
		logging.info("Merge into latest tip of startpoint " + startpoint + " failed")
		
		return
	
	print "Merge from " + branch_from + " into " + branch_to + " was successful. Created issue " + branch_issuename
	commithash = get_commit_hash(branch_issuename)

	commitmessage = branch_issuename + " - \n# Brief summary on line above(<50 chars)\n\n" + \
					"# Describe in detail the change below\nChange-Description:\n\n\n# Describe how to test your change below\n" + \
				 	"Change-TestProcedure:\n\n\n# DO NOT EDIT ANYTHING BELOW HERE\n\nGerrit.startpoint:" + branch_to + \
				 	"\n\nChange-Id: I" + commithash

	logging.info("Writing commit message")

	f = open(branch_issuename + '_commitmessage', 'w')
	f.write(commitmessage)
	f.close()

	subprocess.call(['vim', branch_issuename + '_commitmessage'])
	commitmessage = "" 
			
	f = file(branch_issuename + '_commitmessage', "r")

	for line in f:
		if not line.startswith("#"):
			commitmessage = commitmessage + line
	
	repo.git.commit("-a", '-m', commitmessage)

	f.close()

				
	print "The merge appears to be successful, please check and then push to gerrit using gerrit push"
	

#############################

def review_summary(issue_name):
	logging.info("entering")
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = get_commit_hash(issue_name)
				
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "--current-patch-set", "change:I" + commithash ])
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

#############################

def review_web(issue_name):
	logging.info("entering")
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = get_commit_hash(issue_name)
				
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--commit-message", "--current-patch-set", "change:I" + commithash ])
	decoded = json.loads(info.splitlines()[0])
	uri = decoded['url']
	try:
		webbrowser.open(uri)
	except:
		print "Oh Dear:\n\tIt appears that we can't open a browser or that the uri we have is invalid. Try visiting: " + uri

#############################

def review_patch(issue_name):
	logging.info("entering")
	repo = Repo(os.getcwd())

	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = get_commit_hash(issue_name)
				
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--current-patch-set", "change:I" + commithash ])
	decoded = json.loads(info.splitlines()[0])
	
	ref = decoded['currentPatchSet']['ref']
	logging.info("ref = " + ref)
	
	repo.git.fetch(url, ref)
	patch = subprocess.check_output(['git', "format-patch", "-1", "--stdout", "FETCH_HEAD" ])
	print patch
	
#############################

def review_tool(issue_name):
	logging.info("entering")
	repo = Repo(os.getcwd())

	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = get_commit_hash(issue_name)
				
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--current-patch-set", "change:I" + commithash])
	decoded = json.loads(info.splitlines()[0])
	
	ref = decoded['currentPatchSet']['ref']
	logging.info("ref = " + ref)
	
	repo.git.fetch(url, ref)
		
	repo.git.difftool("--no-prompt", "FETCH_HEAD~..FETCH_HEAD")
	
#############################	

review_type = {
	'web': 		review_web,
	'summary':	review_summary,
	'patch': 	review_patch,
	'tool': 	review_tool,
}

	
def do_review(argv):
	logging.info("entering")
	if len(argv) < 3 or len(argv) > 4 :
		# not a valid star command
		print "Oh Dear:\n\tInvalid command, make sure you specified an issue and try again."
		logging.warning("Invalid command used")
		return
	
	issue_name = argv[2]
	
	if False == issue_exists_on_server(issue_name):
		print "Oh Dear:\n\tThe issue appears not to exist on the server, please check for typos!"
		return
	
	stype = "web"
		
	if len(argv) == 4:
		stype = argv[3]
		
	if stype in review_type:
		logging.info("Summary type running - " + stype)
		review_type[stype](issue_name)
	else:
		logging.warning("Not a Valid review type")
		print "Oh Dear:\n\tThis is not a valid review type. Check for a type!! \n\n\tIf you would like a new type adding let us know!"	

#############################	

def do_cherrypick(argv):
	logging.info("entering")
	repo = Repo(os.getcwd())
	if repo.is_dirty() == True:
		print "Oh Dear:\n\tYour repo is dirty(changed files, unresolved merges etc.\n\n\tPlease resolve these and try again."
		logging.warning("Repo Dirty")
		return
	
	if len(argv) != 3:
		print "Oh Dear:\n\tCherrypick only supports a command with a issue name after it, please try again!"
		logging.warning("Bad command used")
		return
	
	issue_name = argv[2]

	
	url = get_origin_url()
	hostname = get_server_hostname(url)
	port = get_server_port(url)
				
	commithash = get_commit_hash(issue_name)
			
	info = subprocess.check_output(['ssh', hostname, "-p", port, "gerrit", "query", "--format", "JSON", "--current-patch-set", "change:I" + commithash ])
	decoded = json.loads(info.splitlines()[0])
	
	ref = decoded['currentPatchSet']['ref']
	
	logging.info("ref = " + ref)
	
	repo.git.fetch(url, ref)
	repo.git.cherry_pick("FETCH_HEAD")
	
#############################	

def help_start():
	logging.info("entering")
	print "\n\nstart:\n\n\tgit gerrit start <ISSUEID> (STARTPOINT)" + \
	"\n\n\tWhere <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine" + \
	"\n\n\tWhere (STARTPOINT) is an optional argument dictating which branch you are developing on, the default unless set in a config file is master"
	"\n\n\tStart is used to setup a new set of changes, this creates a branch and puts tracking information in your configuration"

#############################	

def help_draft():
	logging.info("entering")
	print "\n\ndraft:\n\n\tgit gerrit draft" + \
	"\n\n\tDraft is used to push the changes on the current branch onto the gerrit server in draft mode, these changes cannot be seen until published"

#############################	

def help_push():
	logging.info("entering")
	print "\n\npush:\n\n\tgit gerrit push" + \
	"\n\n\tpush is used to push the changes on the current branch onto the gerrit server for review. Depending on your" + \
	"\n\tworkflow you will likely need to add reviewers to the issue after pushing"

#############################	

def help_rework():
	logging.info("entering")
	print "\n\nrework:\n\n\tgit gerrit rework <ISSUEID>" + \
	"\n\n\tWhere <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine" + \
	"\n\n\trework will create you a branch called <ISSUEID> where you can make any changes you require and push" + \
	"\n\tthem back to the server, this allows you to take control of a change already pushed by someopne else or" + \
	"\n\treclaim a change if someone else has worked on it"
#############################	

def help_suck():
	logging.info("entering")
	print "\n\nsuck:\n\n\tgit gerrit suck <ISSUEID>" + \
	"\n\n\tWhere <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine" + \
	"\n\n\tsuck downloads a copy of changes for <ISSUEID> from the server into a branch called <ISSUEID>_suck." + \
	"\n\tHere you can build changes for testing etc. You should not use this brnahc to modify the code if you want the" + \
	"\n\tchanges to go back to the server. For this you shuld use rework. Once you have finished with the changes you can delete the branch"
	
#############################	

def help_review():
	logging.info("entering")
	print "\n\nreview:\n\n\tgit gerrit review <ISSUEID> (TYPE)" + \
	"\n\n\tWhere <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine" + \
	"\n\n\tWhere (TYPE) is an optional argument stating the review type wanted, valid types are:" + \
	"\n\t\t\tsummary - This will output a summary of the change on the commandline" + \
	"\n\t\t\tweb - This will take you to the change on the website" + \
	"\n\t\t\tpatch - This will give you a patchset for the change" + \
	"\n\t\t\ttool - This will show you the delta in a GUI tool" + \
	"\n\n\treview is primarily used for getting information about a change, the default review command will take you to the gerrit review page i.e. web mode"
	
#############################	

def help_share():
	logging.info("entering")
	print "\n\nshare:\n\n\tgit gerrit share" + \
	"\n\n\tshare is used to push the current issue to a branch called share/<ISSUEID> on the gerrit server" + \
	"\n\tThis branch can then be accessed like any other branch and shared between multiple people in order" + \
	"\n\tto work together on a feature. This branch can then be merged onto the" + \
	"\n\tdevelopment branches via a standard code review process\n\nSee scrunch command for more info"

#############################	

def help_scrunch():
	logging.info("entering")
	print "\n\nscrunch:\n\n\tgit gerrit scrunch <SHARED/BRANCH> <TARGETBRANCH>" + \
	"\n\n\tWhere <SHARED/BRANCH> is the name of a branch currently shared on the gerrit server" + \
	"\n\tWhere <TARGETBRANCH> is the name of a branch you want the changes onto i.e. master" + \
	"\n\n\tScrunch is used to migrate a shared development branch into a standard gerrit issue that can" + \
	"\n\tthen be pushed to the gerrit server for review. This comman merges the branch from the SERVER not a" + \
	"\n\tlocal copy, as such any local changes you have should be pushed to the server first.\n\nSee share command for more info" 

#############################	
def help_cherrypick():
	logging.info("entering")
	print "\n\n\tcherrypick:\n\n\tgit gerrit cherrypick <ISSUEID>" + \
	"\n\n\t\tWhere <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine" + \
	"\n\n\t\tcherrypick is used to merge a given change on the server into your local branch. Please note, currently dependancy management is not done automatically"

#############################	
def help_version():
	logging.info("entering")
	print "\n\nversion:\n\n\tgit gerrit version <TYPE>" + \
	"\n\n\t\tWhere <TYPE> is an output format, currrently only long and short are supported. long is default" + \
	"\n\n\t\tUsed to print version info, if short is passed as an option then only version number is printed"


#############################	

helpmap = {
	'cherrypick': 	help_cherrypick,
	'draft':		help_draft,
	'push': 		help_push,
	'review': 		help_review,
	'rework': 		help_rework,
	'scrunch':	help_scrunch,
	'share': 	help_share,
	'start': 		help_start,
	'suck': 		help_suck,
	'version': 		help_version,
}

#############################

def do_help(argv):
	logging.info("entering")
	threeargs = False
	if len(argv) == 3:
		if sys.argv[2] in helpmap:
			print "Gerritflow " + sys.argv[2] + " usage:"
			helpmap[sys.argv[2]]()
			return
		
		threeargs = True

	print "Gerrit-flow usage is as follows:"

	print "\tSubcommand list is:"
	print "\t\tcherrypick\n\t\tdraft\n\t\tpush\n\t\treview\n\t\trework\n\t\tscrunch\n\t\tshare\n\t\tstart\n\t\tsuck\n\t\tversion\n\n"
	
	

	if threeargs == True:
		if sys.argv[2] == "all":
			for c in helpmap:
				helpmap[c]()
	else:
		print "For more information run 'git gerrit help <COMMAND>'"
		print "Run 'git gerrit help all' for help output of all gerrit-flow comamnds"

#############################

def do_version(argv):
	logging.info("entering")

	short_mode = False

	if len(argv) == 3:
		if sys.argv[2] == "short":
			short_mode = True

	message = ""
	if short_mode == False:
		message = "Gerrit-flow version is - "

	message = message + str(GERRIT_FLOW_VERSION)

	if short_mode == False:
		message = message + "\n\nFor usage info see git gerrit help"

	print message

#############################	

dispatch = {
	'start': 		do_start,
	'draft':		do_draft,
	'push': 		do_push,
	'rework': 		do_rework,
	'suck': 		do_suck,
	'review': 		do_review,
	'cherrypick': 	do_cherrypick,
	'cherry-pick': 	do_cherrypick,
	'share': 		do_share,
	'scrunch':		do_scrunch,
	'help':			do_help,
	'version':		do_version,
}


def main():
	logging.info("entering")
	logging.info("os.getcwd() = " + os.getcwd())
	logging.info("Number of arguments:" + str(len(sys.argv)))

	logging.info("Arguments:")

	#if no commands are give show help
	if len(sys.argv) == 1:
		do_help(sys.argv)
		return
 
	for a in sys.argv:
		logging.info("\t" + a)

	if sys.argv[1] in dispatch:
		dispatch[sys.argv[1]](sys.argv)
	else:
		logging.warning("No matching command")
		print "Oh Dear:\n\tThere is no matching command, did you RTFM? or do we have a bug?"

#############################	

if __name__ == "__main__":
	rnum = random.randint(100000, 999999)
	logging.basicConfig(format="%(asctime)s: - " + str(rnum) + " - %(filename)s: -  %(funcName)s() - %(lineno)d : %(message)s", level=logging.DEBUG, filename='/tmp/gerrit-flow.log')
	main()
