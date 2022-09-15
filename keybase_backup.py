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


def kb_call(method, options={}):
    """
    call keybase api with given method and options
    and return the response

    due to lack of tcp listener for the api
    it's based on subprocess.run
    """
    data = {
        "method": method,
        "params": {
            "options": options,
        },
    }
    result = subprocess.run(
        ["/usr/bin/keybase", "chat", "api", "-m", json.dumps(data)],
        capture_output=True,
        check=True,
    )
    output = result.stdout.decode("UTF-8")[:-1]
    response = json.loads(output)
    return response["result"]


def download(message):
    """
    Given a message download the attachment from the message
    """
    if message["msg"]["content"]["type"] != "attachment":
        print("The message is not an attachment")
        return

    message_id = message["msg"]["id"]
    conversation_id = message["msg"]["conversation_id"]
    folder = chat2folder(message["msg"]["channel"]["name"])
    attachment_filename = "{}/{}_{}".format(
        folder,
        str(message_id),
        message["msg"]["content"]["attachment"]["object"]["filename"],
    )
    print("Writing " + attachment_filename)
    file_exists = os.path.exists(attachment_filename)
    if not file_exists:
        kb_call("download", {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "output": attachment_filename,
        })


def get_chat_history(conversation_id, page=None):
    """
    wrapper to get a chat history, base on it's conversation_id
    """
    options = {
        "conversation_id": conversation_id,
    }
    if page is not None:
        options = options | {
            "pagination": {
                "next": page,
                "num": 1000,
            }
        }

    response = kb_call("read", options)

    messages = response["messages"]
    last = response["pagination"]["last"]
    next_page = response["pagination"]["next"]

    if last:
        return messages

    return messages + get_chat_history(conversation_id, next_page)

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
    chat_list = kb_call("list")
    # better do it when we are online
    if not chat_list["offline"]:
        for conversation in chat_list["conversations"]:
            if conversation["id"] not in EXCLUDE:
                folder = chat2folder(conversation["channel"]["name"])
                history = get_chat_history(conversation["id"])
                save_history(history, folder)
                save_attachments(history)


if __name__ == "__main__":
    get_chat_list()
