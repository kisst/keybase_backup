#!/usr/bin/env python3
"""
This script is backing up media, and chat history from Keybase
"""
import os
import sys
import subprocess
import json

EXCLUDE = [
    "0000f4820d97ad9d49266219c985627d54a7e619b6953779ed5e85abb767b39d",
    "0000d5ba71470610a40b4d32af53a52775cc561589525d7b21bad9ec057b6aac",
    "0000afd23621e31fac3b212ab0b9728141301dcf6995eb39726a3d69752cfb68",
]


def chat2folder(chat_name):
    """
    Covert a chat name into folder name
    and ensure that the folder exist
    """
    backup_dir = os.path.join(
        os.path.expanduser("~"), "Documents/Personal/Backup/Keybase/"
    )
    folder_name = backup_dir + chat_name.replace(",", "_")
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def kb_call(api_data):
    """
    Given a dict, send it to keybase api,
    and return the response

    due to lack of tcp listener for the api
    it's based on subprocess.run
    """
    if isinstance(api_data, dict):
        result = subprocess.run(
            ["/usr/bin/keybase", "chat", "api", "-m", json.dumps(api_data)],
            capture_output=True,
            check=True,
        )
        dict_str = result.stdout.decode("UTF-8")[:-1]
        response = json.loads(dict_str)
        return True, response
    else:
        print("The input isn't a dict, we can't convert it to JSON")
        return False, None


def get_next(pagination):
    """
    Helper function to detect if it's last page
    if not return the next page ID
    """
    try:
        if pagination["last"]:
            return True, None
    except KeyError:
        next_page = pagination["next"]
        return False, next_page


def download(message):
    """
    Given a message download the attachment from the message
    """
    if message["msg"]["content"]["type"] != "attachment":
        print("The message is not an attachment")
        return False
    else:
        message_id = message["msg"]["id"]
        conversation_id = message["msg"]["conversation_id"]
        folder = chat2folder(message["msg"]["channel"]["name"])
        attachment_filename = "{}/{}_{}".format(
            folder,
            str(message_id),
            message["msg"]["content"]["attachment"]["object"]["filename"],
        )
        download_ask = {}
        download_ask["method"] = "download"
        download_ask["params"] = {}
        download_ask["params"]["options"] = {}
        download_ask["params"]["options"]["message_id"] = message_id
        download_ask["params"]["options"]["output"] = attachment_filename
        download_ask["params"]["options"]["conversation_id"] = conversation_id
        print("Writing " + attachment_filename)
        file_exists = os.path.exists(attachment_filename)
        if not file_exists:
            kb_call(download_ask)


def get_chat_history(conversation_id, page=None):
    """
    wrapper to get a chat history, base on it's conversation_id
    """
    chat_history = []
    chat_history_ask = {}
    chat_history_ask["method"] = "read"
    chat_history_ask["params"] = {}
    chat_history_ask["params"]["options"] = {}
    chat_history_ask["params"]["options"]["conversation_id"] = conversation_id
    if page:
        chat_history_ask["params"]["options"]["pagination"] = {}
        chat_history_ask["params"]["options"]["pagination"]["next"] = page
        chat_history_ask["params"]["options"]["pagination"]["num"] = 1000
    status, chat_history_part = kb_call(chat_history_ask)
    if status:
        chat_history = chat_history + chat_history_part["result"]["messages"]
        last, next_page = get_next(chat_history_part["result"]["pagination"])
        if not last:
            chat_history_last_part = get_chat_history(conversation_id, next_page)
            if chat_history_last_part:
                chat_history = chat_history + chat_history_last_part
        return chat_history
    else:
        print("Unsuccesfull call")
        return []


def save_history(history, folder):
    """
    Write the json data given in history
    to the given
    """
    filename = folder + "/chat_history.json"
    print("Writing " + filename)
    with open(filename, "w") as outfile:
        json.dump(history, outfile)


def save_attachments(history):
    """
    Given a chat history pick the attachments and save them
    """
    for message in history:
        if message["msg"]["content"]["type"] == "attachment":
            download(message)


def get_chat_list():
    """
    wrapper to get the list of chats
    and loop across them for backup
    this is the main function of the script
    """
    chat_list_ask = {}
    chat_list_ask["method"] = "list"
    status, chat_list = kb_call(chat_list_ask)
    # better do it when we are online
    if not chat_list["result"]["offline"] and status:
        for conversation in chat_list["result"]["conversations"]:
            if conversation["id"] not in EXCLUDE:
                folder = chat2folder(conversation["channel"]["name"])
                history = get_chat_history(conversation["id"])
                save_history(history, folder)
                save_attachments(history)


get_chat_list()
