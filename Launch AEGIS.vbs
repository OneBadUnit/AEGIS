Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

ProjectPath = FSO.GetParentFolderName(WScript.ScriptFullName)
FrontendPath = ProjectPath & "\frontend"

BackendCommand = "cmd /k cd /d """ & ProjectPath & """ && python main.py"
FrontendCommand = "cmd /k cd /d """ & FrontendPath & """ && npm run dev"

BrowserCommand = "http://127.0.0.1:5175"

' Start backend
WshShell.Run BackendCommand, 1, False

' Give backend time to bind port 8002
WScript.Sleep 4000

' Start frontend
WshShell.Run FrontendCommand, 1, False

' Give Vite time to initialize
WScript.Sleep 5000

' Open browser
WshShell.Run BrowserCommand, 1, False