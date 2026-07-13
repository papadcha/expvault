; Εγκατάσταση/απεγκατάσταση της γραμματοσειράς Iosevka ώστε οι εξαγωγές
; Word/Excel να τη βρίσκουν ως system font (το PDF την ενσωματώνει ήδη
; απευθείας, οπότε δεν το χρειάζεται). $installMode είναι "all" (per-machine,
; απαιτεί ήδη admin/UAC) ή "CurrentUser" (per-user, χωρίς admin) — βλ.
; multiUser.nsh του electron-builder.

!include "WinMessages.nsh"

!macro installIosevkaFont
  ${if} $installMode == "all"
    StrCpy $R5 "$WINDIR\Fonts"
    StrCpy $R6 HKLM
  ${else}
    StrCpy $R5 "$LOCALAPPDATA\Microsoft\Windows\Fonts"
    StrCpy $R6 HKCU
  ${endif}

  CreateDirectory "$R5"
  CopyFiles /SILENT "$INSTDIR\resources\assets\fonts\Iosevka-Regular.ttf" "$R5\Iosevka-Regular.ttf"
  CopyFiles /SILENT "$INSTDIR\resources\assets\fonts\Iosevka-Bold.ttf" "$R5\Iosevka-Bold.ttf"

  WriteRegStr $R6 "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka (TrueType)" "Iosevka-Regular.ttf"
  WriteRegStr $R6 "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka Bold (TrueType)" "Iosevka-Bold.ttf"

  System::Call 'gdi32::AddFontResource(t) i ("$R5\Iosevka-Regular.ttf") .r0'
  System::Call 'gdi32::AddFontResource(t) i ("$R5\Iosevka-Bold.ttf") .r0'
  SendMessage ${HWND_BROADCAST} ${WM_FONTCHANGE} 0 0 /TIMEOUT=5000
!macroend

!macro uninstallIosevkaFont
  ${if} $installMode == "all"
    StrCpy $R5 "$WINDIR\Fonts"
    StrCpy $R6 HKLM
  ${else}
    StrCpy $R5 "$LOCALAPPDATA\Microsoft\Windows\Fonts"
    StrCpy $R6 HKCU
  ${endif}

  System::Call 'gdi32::RemoveFontResource(t) i ("$R5\Iosevka-Regular.ttf") .r0'
  System::Call 'gdi32::RemoveFontResource(t) i ("$R5\Iosevka-Bold.ttf") .r0'

  DeleteRegValue $R6 "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka (TrueType)"
  DeleteRegValue $R6 "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka Bold (TrueType)"

  Delete "$R5\Iosevka-Regular.ttf"
  Delete "$R5\Iosevka-Bold.ttf"

  SendMessage ${HWND_BROADCAST} ${WM_FONTCHANGE} 0 0 /TIMEOUT=5000
!macroend

!macro customInstall
  DetailPrint "Εγκατάσταση γραμματοσειράς Iosevka..."
  !insertmacro installIosevkaFont
!macroend

!macro customUnInstall
  !insertmacro uninstallIosevkaFont
!macroend
