!include MUI2.nsh

Name "RD-USB"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_RUN_TEXT "Start application"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

OutFile "dist/rd-usb-install.exe"

InstallDir "$PROGRAMFILES64\rd-usb"
InstallDirRegKey HKLM "Software\rd-usb" "Install_Dir"
RequestExecutionLevel admin

Section "Dummy Section" SecDummy
    ; program files
    SetOutPath $INSTDIR
    RMDir /r $INSTDIR
    File /r dist\rd-usb\*.*

    ; shortcuts
    CreateDirectory "$SMPROGRAMS\rd-usb"
    CreateShortcut "$SMPROGRAMS\RD-USB\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    CreateShortcut "$SMPROGRAMS\RD-USB\RD-USB.lnk" "$INSTDIR\rd-usb.exe"

    ; reinstall helper
    WriteRegStr HKLM Software\rd-usb "Install_Dir" "$INSTDIR"

    ; uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\rd-usb" "DisplayName" "RD-USB"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\rd-usb" "DisplayIcon" "$INSTDIR\static\img\icon.ico"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\rd-usb" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\rd-usb" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\rd-usb" "NoRepair" 1

    ; edge webview2 runtime
    Call installEdgeWebView2
SectionEnd

Section "Uninstall"
    ; program files
    RMDir /r $INSTDIR

    ; shortcuts
    RMDir /r "$SMPROGRAMS\rd-usb"

    ; registry
    DeleteRegKey HKLM "Software\rd-usb"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\rd-usb"
SectionEnd

Function LaunchLink
    ExecShell "" "$SMPROGRAMS\rd-usb\RD-USB.lnk"
FunctionEnd

# Install edge webview2 by launching the bootstrapper
# See https://docs.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution#online-only-deployment
# MicrosoftEdgeWebview2Setup.exe download here https://go.microsoft.com/fwlink/p/?LinkId=2124703
Function installEdgeWebView2
	# If this key exists and is not empty then webview2 is already installed
	ReadRegStr $0 HKLM "SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
	ReadRegStr $1 HKCU "Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
	DetailPrint "WebView2 machine version: $0"
	DetailPrint "WebView2 user version: $1"

	${If} $0 == ""
	${AndIf} $1 == ""
		SetDetailsPrint both
		DetailPrint "Installing: WebView2 Runtime, this may take a while, please wait..."
		SetDetailsPrint listonly

		InitPluginsDir
		CreateDirectory "$pluginsdir\webview2bootstrapper"
		SetOutPath "$pluginsdir\webview2bootstrapper"
		File "bin\MicrosoftEdgeWebview2Setup.exe"
		ExecWait '"$pluginsdir\webview2bootstrapper\MicrosoftEdgeWebview2Setup.exe" /silent /install'

		SetDetailsPrint both
	${Else}
	    DetailPrint "WebView2 is already installed"
	${EndIf}
FunctionEnd
