XBMCnfoMoviesImporter.bundle-for-Plex
=====================================
The agent is part of the Unsupported Appstore plugin. Installing it, will make
installation and updates of the agent very easy. You can find the appstore here:
https://forums.plex.tv/index.php/topic/151068-unsupported-app-store-as-in-totally-unsupported-is-currently-offline/

Alternatively you can install manually by downloading the [zipped bundle](https://github.com/gboudreau/XBMCnfoMoviesImporter.bundle/archive/master.zip) from github, extract it, rename it to **XBMCnfoMoviesImporter.bundle**.

User MattJ from the plex forum reported the following steps to install on ubuntu 14.04:
1.  Download from github and unzip
2.  Remove "-master" from the end of both folder names.
3.  Copy them to the folder:  /var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins
4.  Find the group number for user "plex" by command "id plex".
5.  "cd" to folder in step 3 and change ownership of both XBMC bundles: "sudo chown plex:{gid} XBMC*"
6.  run "sudo service plexmediaserver restart".
Done.
