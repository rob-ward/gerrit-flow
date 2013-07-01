gerrit-flow
===========

gerrit flow is a set of functionality to support interaction with the gerrit code review tool (http://code.google.com/p/gerrit/) 

This tool supports interaction with the gerrit server in a way that allows a number of workflows to be used in development.

Please report any bugs to or feature requests to;
 			https://github.com/rob-ward/gerrit-flow
 			

Getting started
---------------

gerrit-flow provides a set of command aliases to git. The commands make creating patchsets for gerrit easier while providing other functionlaity such as the ability to access information from the gerrit server.

The standard commands provided are:
		start
		draft
		push
		rework
		suck
		review
		cherrypick
		

A standard workflow for gerrit is:

   Using git gerrit start create a local branch for your changes.
	
   You now make any changes you want with as many commits as you wish.
	
   When you want to put the changes on the server for review you do a git gerrit push
	
   You will be asked to complete a commit message.
	
   Upon completion this change can then be seen on the server
	

Installing gerrit-flow
-------------------

Download a copy of the gerrit code from github

Add the following to you ~/.gitconfig:

[alias]
	gerrit = !\<DOWNLOAD LOCATION\>/gerrit.py
	


Install dependacies using:
	sudo easy_install GitPython
	

Gerrit-flow Usage
------------------
	Subcommand list is:
		cherrypick
		draft
		push
		review
		rework
		scrunch
		share
		start
		suck
		version




suck:

	git gerrit suck <ISSUEID>

	Where <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine

	suck downloads a copy of changes for <ISSUEID> from the server into a branch called <ISSUEID>_suck.
	Here you can build changes for testing etc. You should not use this brnahc to modify the code if you want the
	changes to go back to the server. For this you shuld use rework. Once you have finished with the changes you can delete the branch


start:

	git gerrit start <ISSUEID> (STARTPOINT)

	Where <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine

	Where (STARTPOINT) is an optional argument dictating which branch you are developing on, the default unless set in a config file is master


rework:

	git gerrit rework <ISSUEID>

	Where <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine

	rework will create you a branch called <ISSUEID> where you can make any changes you require and push
	them back to the server, this allows you to take control of a change already pushed by someopne else or
	reclaim a change if someone else has worked on it


scrunch:

	git gerrit scrunch <SHARED/BRANCH> <TARGETBRANCH>

	Where <SHARED/BRANCH> is the name of a branch currently shared on the gerrit server
	Where <TARGETBRANCH> is the name of a branch you want the changes onto i.e. master

	Scrunch is used to migrate a shared development branch into a standard gerrit issue that can
	then be pushed to the gerrit server for review. This comman merges the branch from the SERVER not a
	local copy, as such any local changes you have should be pushed to the server first.

	See share command for more info


draft:

	git gerrit draft

	Draft is used to push the changes on the current branch onto the gerrit server in draft mode, these changes cannot be seen until published


version:

	git gerrit version <TYPE>

	Where <TYPE> is an output format, currrently only long and short are supported. long is default

	Used to print version info, if short is passed as an option then only version number is printed


push:

	git gerrit push

	push is used to push the changes on the current branch onto the gerrit server for review. Depending on your
	workflow you will likely need to add reviewers to the issue after pushing


cherrypick:

	git gerrit cherrypick <ISSUEID>

	Where <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine

	cherrypick is used to merge a given change on the server into your local branch. Please note, currently dependancy management is not done automatically


share:

	git gerrit share

	share is used to push the current issue to a branch called share/<ISSUEID> on the gerrit server
	This branch can then be accessed like any other branch and shared between multiple people in order
	to work together on a feature. This branch can then be merged onto the
	development branches via a standard code review process

	See scrunch command for more info


review:

	git gerrit review <ISSUEID> (TYPE)

	Where <ISSUEID> is a unique id, this is normally taken from an issue control system such as redmine

	Where (TYPE) is an optional argument stating the review type wanted, valid types are:
			summary - This will output a summary of the change on the commandline
			web - This will take you to the change on the website
			patch - This will give you a patchset for the change
			tool - This will show you the delta in a GUI tool

	review is primarily used for getting information about a change, the default review command will take you to the gerrit review page i.e. web mode
