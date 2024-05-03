#

import sys
import zipfile
import subprocess
import os

# Script for transformation of archived websites crawled with Teleport Pro, Offline Explorer Pro and Offline Web Archiv
# (exported to folder structure) to WARC format
# input: folder containing the "original" legacy crawl job
# output is written to CWD, to a folder with the same name as original crawl job

# The script goes through all subfolders on the first level of the given original crawl job.
# It first calls the warcit-transformer for each folder - in this step the html files are checked for relative paths
# linking to other domains.
# Subsequently warcit is called and converts the folder structure to a WARC file.
# The specific configuration of warcit may have to be adapted (subprocess in last line of file).

params = sys.argv
origin_folder_path = params[1]

path_as_list = origin_folder_path.strip('"')
path_as_list = path_as_list.strip('/')
path_as_list = path_as_list.rsplit('/', 2)
origin_folder_name = path_as_list[2]
#print(origin_folder_name)
	
output_folder_name = origin_folder_name
output_folder_path = os.path.join(os.getcwd() + ('/') + output_folder_name)
#print(output_folder_path)

if not os.path.exists(output_folder_path):
	os.mkdir(output_folder_path)
os.chdir(output_folder_path)
log_folder = os.path.join(os.getcwd() + ('/') + "log")
if not os.path.exists(log_folder):
	os.mkdir(log_folder)
warc_folder = os.path.join(os.getcwd() + ('/') + "warcs")
if not os.path.exists(warc_folder):
	os.mkdir(warc_folder)


print("CWD is " + os.getcwd())
print("As origin folder the following path is used: " + origin_folder_path)
print("As output folder the following path is used " + output_folder_path)

#Methode zum Auflisten von 
def list_subfolders(orig_fld):
	
	subfolder_list = []
	for folder in os.listdir(orig_fld):
		subfolder_list.append(folder)
	return(subfolder_list)


domain_list = list_subfolders(origin_folder_path)

for entry in domain_list:
	print(entry)
	website = 'http://' + entry + '/'
	print('website: ' + website)
	source_path = os.path.join(origin_folder_path + ('/') + entry)
	trans_result_doc = os.path.join(output_folder_path + ('/transformations/') + entry + '-trans-result.yaml')
	print('trans-result-doc: ' + trans_result_doc)
	print('source path: ' + source_path)
	transform_results_file = entry + "-trans-result.yaml"
	website_name_for_job = website.replace("http", "")
	website_name_for_job = website_name_for_job.replace(":", "")
	website_name_for_job = website_name_for_job.replace("/", "")
	website_name_for_job = website_name_for_job.replace(".", "_")
	ct = datetime.datetime.now().strftime("%y%m%d%H%M%S")
	website_name_for_job = website_name_for_job + ct
	job_name = 'warcs/' + website_name_for_job
	log = 'log/' + website_name_for_job + '.log'
	subprocess.run(["warcit-transformer", "--results", transform_results_file, website, source_path])

	subprocess.run(["warcit", "--transformations", trans_result_doc, "-n", job_name, "-o", "--use-magic", "magic",
			"--no-xhtml", "--log", log, "--mime-overrides=*.php*=text/html,*.gif*=image/gif,*.*7em*=text/html,*.*5em*=text/html,"
			"*.htm*=text/html,*@printme*=text/html,*.css*=text/css,*.js=text/javascript",
			"--index-files", "index.html,index.htm,default.htm,default.html", website, source_path])






