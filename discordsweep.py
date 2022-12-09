#!/usr/bin/env python3
import argparse
import requests
import time
import calendar

banner = r'''
 (                           (                         
 )\ )                   (    )\ )                      
(()/( (            (    )\ )(()/((  (     (   (        
 /(_)))\ (   (  (  )(  (()/( /(_))\))(   ))\ ))\`  )   
(_))_((_))\  )\ )\(()\  ((_)|_))((_)()\ /((_)((_)(/(   
 |   \(_|(_)((_|(_)((_) _| |/ __|(()((_|_))(_))((_)_\  
 | |) | (_-< _/ _ \ '_/ _` |\__ \ V  V / -_) -_) '_ \) 
 |___/|_/__|__\___/_| \__,_||___/\_/\_/\___\___| .__/  
                                               |_|     

====> Author: James Fox (@jamesfoxdev)
====> Repo: github.com/jamesfoxdev
====> License: MIT

'''

API_URL = "https://discordapp.com/api/v6/"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) discord/0.0.9 Chrome/69.0.3497.128 Electron/4.0.8 Safari/537.36"

def retreiveMessages(serverID, userID, authToken, deleteCap=None, minAgeHours=None):
    deleteList = []
    offset = 0
    retryCap = 5
    messageFound = False
    now = calendar.timegm(time.gmtime())
    while True:
        if retryCap == 0:
            print(f"[ERROR] Retry cap ({retryCap}) hit, exiting...")
            exit(1)

        if len(deleteList) == deleteCap:
            print("[INFO] Delete cap reached, moving on.")
            return deleteList

        searchRes = requests.get(f"{API_URL}guilds/{serverID}/messages/search", headers={
            "authorization":authToken,
            "user-agent":USER_AGENT
        }, params={
            "author_id":userID,
            "offset":offset,
            "include_nsfw":True
        })

        if searchRes.status_code == 400:
            print("[WARNING] 400 Status code")
            return deleteList
        if searchRes.status_code == 429:
            try:
                dcResp = searchRes.json()
                if "retry_after" in dcResp:
                    print(f"[WARNING] Being rate limited... Waiting {dcResp['retry_after']} s")
                    time.sleep(dcResp['retry_after'])
                    continue
            except:
                print("[WARNING] 429, too many requests! Waiting 30s...")
                time.sleep(30)
                continue
        if searchRes.status_code != 200:
            print(f"[ERROR] Unexpected error {searchRes.status_code}")
            retryCap = retryCap - 1
            continue

        dcResp = searchRes.json()

        if "retry_after" in dcResp:
            print(f"[WARNING] Being rate limited... Waiting {dcResp['retry_after']} s")
            time.sleep(dcResp['retry_after'])
            continue

        for messageBlock in dcResp["messages"]:
            for message in messageBlock:
                # Only add to the delete list if the message author matches our user and isn't added already
                if message["author"]["id"] == userID and not any(d["mid"] == message["id"] for d in deleteList):
                    messageFound = True
                    timestamp = ((int(message["id"]) >> 22) + 1420070400000)/1000
                    if minAgeHours is None or timestamp < now - minAgeHours*60*60:
                        deleteList.append({
                            "cid":message["channel_id"],
                            "mid":message["id"]
                        })
        
        # If no valid messages (ignoring timestamp) were found on the next page, assume no more are left
        if not messageFound:
            return deleteList

        offset += 25

        messageFound = False
        print(f"[INFO] Current message count {len(deleteList)}")

    return deleteList

def deleteMessages(messages, authToken):
    for message in messages:
        deleteRes = requests.delete(f"{API_URL}/channels/{message['cid']}/messages/{message['mid']}", headers={
            "authorization":authToken,
            "user-agent":USER_AGENT
        })

        if deleteRes.status_code != 204:
            print(f"[ERROR] Unexpected error {deleteRes.status_code}")
            try:
                dcResp = deleteRes.json()
                if "retry_after" in dcResp:
                    print(f"[WARNING] Being rate limited... Waiting {dcResp['retry_after']} s")
                    time.sleep(dcResp['retry_after'])
                    continue
            except:
                continue

parser = argparse.ArgumentParser()
parser.add_argument("serverID", help="Server ID to wipe from", type=str)
parser.add_argument("userID", help="Your Discord user ID")
parser.add_argument("authToken", help="Discord authorization token", type=str)
parser.add_argument("-c", "--cap", help="Cap the amount of messages to delete", type=int)
parser.add_argument("-a", "--age", help="Minimum age of messages to delete, in hours", type=int)
args = parser.parse_args()

print(banner)
print(f"[INFO] Searching for messages from user {args.userID} in {args.serverID}")

deleteList = retreiveMessages(args.serverID, args.userID, args.authToken, deleteCap=args.cap, minAgeHours=args.age)
print(f"[SUCCESS] Retreived all messages ({len(deleteList)}) from the server. Deleting...")
deleteMessages(deleteList, args.authToken)
print("[SUCCESS] Done!")
