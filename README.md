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
	

