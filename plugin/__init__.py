from .ui.chat_dock import ChatDock

def getMetaData():
    return {}

def register(app):
    return {
        "extension": [
            ChatDock()
        ]
    }
