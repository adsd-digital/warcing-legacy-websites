# warcing-legacy-websites

WARNING: This is script is not finally tested and still has bugs that need solving (see below and in code).

The script warcing-legacy-folder.py can be used to transform websites that have been downloaded with specific software to a folder structure to the WARC format.
The script has been developed and tested for websites downloaded with
- Teleport Pro (versions from ca. 1999-2004)
- Offline Explorer Pro (versions from ca. 2004-2011)
- Offline Web Archiv (versions from ca. 2008-2018), websites exported from database to folder structure.

The output directory structure of these crawlers has the following form:

├── JOB_NAME
   ├── www.example.org
   ├── www.next-example.com
   └── another-domain.com     

In the downloaded html files any links to domains within the crawl are stored as relative paths, e.g. ../../../www.example.org
Before adding these files to a WARC container these paths have to be made absolute, else the linking e.g. within pywb and other playback software will not work.

To this purpose the script calls for every subfolder first the html-transformer which has been implemented as a module of warcit, in analogue to the warcit-converter.
All html files are checked for links that have to be adapted, if changes are made, a new version of the html file is stored and the new path documented in the transformation-result.yaml.

The script then calls calls for every subfolder warcit while including this trans-results.yaml - in the resulting WARC both the "original" and the transformed html file are stored. 

The final output is a WARC file for every folder found on the first level beneath the input folder.

## RUNNING:

To get the script warcing-legacy-folder.py running, you need to have an adapted version of warcit installed.
warcit can be installed from https://pypi.org/project/warcit/. For the transformer to work, the original warcit.py file has to be replaced and the html_transformer.py and rules.yaml need to be added. Furthermore the html_transformer has to be added to the path.

You then can call the script, e.g.

$ python3 warcing-legacy-websites.py path/to/JOB_NAME

The output is written to a folder with the name JOB_NAME in the current working directory.

The script has only been tested on Ubuntu.

## TODOs, Bugs and warnings:

The script should output WARCs that can be replayed by pywb.

But there are still a few bugs and a lot of things that need to be changed:


### Html transformation:

- 	The relative paths in the html files may only be replaced if followed by a domain. To detect the domain first a regex is employed. The last part of this regex should be the top level domain. This is matched against a list of top level domains.
	At the moment this list is hard coded, it should be replaced by a reference document. 
	The list is also far from complete. To check for missing top level domains all extensions found are written to the tld.csv mentioned below (logging). 
-	The "../" part of the detected (wrong) relativ file paths is at the moment replaced by "http://". It remains to be tested if a differentiation between http and https is necessary and if so how the information on which protocoll to choose can be detected.
-	The transformed html files are stored with the timestamp of the moment they are changed. For replay this is not ideal. The method for overwriting the timestamp with the timestamp of the original file is implemented but at the moment commented out.
	This is due to the fact that in replay the transformed html file is not shown because there is another file with the exact same url and timestamp. 
- 	The html files are detected by the method ... It remains to be tested if all relevant files are found by this method. To check for files with unclear format identification all files that are not identified via this message are assigned text/html?? as mime type. 
	This way they are treated as html files but can be filtered out via the command line (see logging). 

### Logging:

- 	The detected file types are at the moment only output to the commandline. The file types are needed for testing purposes (see html transformation).
	To get an overview of these mime types you can of course add something like " > filetype.csv" to the call in the commandline. But then you will also get a few other outputs to that file.
-	There is a tld.csv produced, where all the extensions handled as potential top level domains are stored. The header row is at the moment added everytime a new subfolder is called. 

### Documentation:

- 	Ideally the WARC should contain information on how the html files have been transformed during this process.
-	The output of the software products also offers a few specific files/properties:
	-	Teleport Pro: After each "href" there is the tag "tpp apps" added, where the original path is stored. 
		Potentially for this software there could also be a further check added to test if the new url has been replaced correctly.
	- 	Offline Explorer Pro: in folders with transformed files there is a proprietary WD3-File, readable with a basic text editor are only only the file names and the timestamp
		In a newer versions of the Offline Explorer Pro, there is also a added default.htm, that can be used as entry page to the downloaded sites. 
	-	Offline Web Archiv: in the same folders as the domain subfolders there is a Properties.xml, where the configuration of the crawl job is stored.
	These additional files are at the moment also added to a WARC file - the Properties.xml becomes its own WARC file, the WD3-Files are added to the respective WARC Files. 
	This way this information is still potentially accessible, but it needs explanation, documentation or potentially should be stored elsewhere.

### General:

- 	It might make sense to add all output warcs to one warc file.

