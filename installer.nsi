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
RequestExecutionLevel admin

Section "Dummy Section" SecDummy
    SetOutPath $INSTDIR
    RMDir /r $INSTDIR
    File /r dist\rd-usb\*.*
    WriteUninstaller "$INSTDIR\uninstall.exe"
    CreateDirectory "$SMPROGRAMS\rd-usb"
    CreateShortcut "$SMPROGRAMS\RD-USB\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    CreateShortcut "$SMPROGRAMS\RD-USB\RD-USB.lnk" "$INSTDIR\rd-usb.exe"
SectionEnd

Section "Uninstall"
    Delete "$SMPROGRAMS\rd-usb\Uninstall.lnk"
    Delete "$SMPROGRAMS\rd-usb\RD-USB.lnk"
    RMDir /r $INSTDIR
SectionEnd

Function LaunchLink
  ExecShell "" "$SMPROGRAMS\rd-usb\RD-USB.lnk"
FunctionEnd
