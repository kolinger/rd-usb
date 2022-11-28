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
