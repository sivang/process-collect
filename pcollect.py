#!/usr/bin/env python
"""
Just like garbage collection, sometimes we need a script
of this sort to garbage collect hanging processes while
we're on our way to make our whole system better.

(This is the reality of working with production, sometimes
you have to use duck tape untill you fix an elusive bug,
change your tooling or do a massive obtrusive upgrade
of underlying frameworks and services.)

It should be self explantory to configure this, 
after which it can be periodically executed using CRON
at a desired interval.

- sivan@vitakka.co
"""

import psutil
from datetime import datetime
import sys
import time

def returns_processes(attrs=None):
	proc_list = []
	for p in psutil.process_iter():
		try:
			if attrs:
				pinfo =  p.as_dict(attrs)
			else:
				pinfo = p.as_dict()
		except psutil.NoSuchProcess:
			pass
		else:
			proc_list.append(pinfo)
	return proc_list

def process_live_time(pinfo):
	now = datetime.now()
	then = datetime.fromtimestamp(pinfo['create_time'])
	tdelta = now - then
	seconds = tdelta.total_seconds()
	return seconds


	

def filter_processes(proc_list, search_string, username, max_time=0):
	filtered = [p 
			for p in proc_list if  
			(search_string in p['name'] or 
			search_string in "".join(p['cmdline'])) and 
			username == p['username']]

	if not max_time:
		return filtered

		
	max_lived = [p 	for p in filtered if
			process_live_time(p) >= max_time]
	return max_lived

def filter_cpu_percent(proc_list, cpu_percent=0):
	result_list = []
	for p in proc_list:
		try:
			p['cpu_percent'] = psutil.Process(p['pid']).cpu_percent(interval=0.8)
		except psutil.NoSuchProcess:
			pass
		if p['cpu_percent'] == cpu_percent:
			result_list.append(p)

	return result_list


def collect_log(pids, source_path, target_path):
	with open(source_path) as source_file:
		for orig_line in source_file:
			fields = [i for i in orig_line.split() if i!='']
			if len(fields) < 3:
				continue
			try:
				# pid is assumed to be at the 
				# second field of a line in the log
				# file.
				p = int(fields[2]) # need be changed if log format changes
			except:
				continue
			if p in pids:
				print "found p in pids!"
				with open(
					target_path + 	"__" + str(p) + ".log", 'a') as target_file:
						target_file.write(orig_line)


def main():
	plist = returns_processes(attrs=['pid',
					 'username',
					 'name',
					 'cmdline',
					 'cpu_percent',
					 'create_time'])
	filtered = filter_processes(plist, '[YOUR_PROCESS_NAME]', '[OWNER_USER]', 60*60)
	filtered = filter_cpu_percent(filtered)
	# killem' all
	killed = []
	for p in filtered:
		try:
			psutil.Process(p['pid']).kill()
			killed.append(p)
		except psutil.NoSuchProcess:
			pass
	pids = map(lambda pr: pr['pid'], killed)

	if len(pids)==0:
		sys.exit(0)

	collect_log(pids, '/var/log/[YOUR_DIR_HERE]/[LEADING_LOG_FILE]',
		'/var/log/[YOUR_DIR_HERE]/[YOUR_SERVICE_NAME]__')

			
if __name__ == "__main__":
	main()
	
