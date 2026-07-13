; Εγκατάσταση/απεγκατάσταση της γραμματοσειράς Iosevka ώστε οι εξαγωγές
; Word/Excel να τη βρίσκουν ως system font (το PDF την ενσωματώνει ήδη
; απευθείας, οπότε δεν το χρειάζεται). $installMode είναι "all" (per-machine,
; απαιτεί ήδη admin/UAC) ή "CurrentUser" (per-user, χωρίς admin) — βλ.
; multiUser.nsh του electron-builder.
;
; Σημείωση: DeleteRegValue/WriteRegStr θέλουν literal root key (HKLM/HKCU),
; όχι μεταβλητή — γι' αυτό οι κλάδοι all/CurrentUser επαναλαμβάνονται.

!include "WinMessages.nsh"

!macro installIosevkaFont
  ${if} $installMode == "all"
    StrCpy $R5 "$WINDIR\Fonts"
  ${else}
    StrCpy $R5 "$LOCALAPPDATA\Microsoft\Windows\Fonts"
  ${endif}

  CreateDirectory "$R5"
  CopyFiles /SILENT "$INSTDIR\resources\assets\fonts\Iosevka-Regular.ttf" "$R5\Iosevka-Regular.ttf"
  CopyFiles /SILENT "$INSTDIR\resources\assets\fonts\Iosevka-Bold.ttf" "$R5\Iosevka-Bold.ttf"

  ; Το HKLM (system Fonts folder) δέχεται μόνο filename· το HKCU (per-user,
  ; εκτός default Fonts folder) χρειάζεται το πλήρες path, αλλιώς τα Windows
  ; δεν βρίσκουν τη γραμματοσειρά.
  ${if} $installMode == "all"
    WriteRegStr HKLM "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka (TrueType)" "Iosevka-Regular.ttf"
    WriteRegStr HKLM "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka Bold (TrueType)" "Iosevka-Bold.ttf"
  ${else}
    WriteRegStr HKCU "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka (TrueType)" "$R5\Iosevka-Regular.ttf"
    WriteRegStr HKCU "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka Bold (TrueType)" "$R5\Iosevka-Bold.ttf"
  ${endif}

  System::Call 'gdi32::AddFontResource(t) i ("$R5\Iosevka-Regular.ttf") .r0'
  System::Call 'gdi32::AddFontResource(t) i ("$R5\Iosevka-Bold.ttf") .r0'
  SendMessage ${HWND_BROADCAST} ${WM_FONTCHANGE} 0 0 /TIMEOUT=5000
!macroend

!macro uninstallIosevkaFont
  ${if} $installMode == "all"
    StrCpy $R5 "$WINDIR\Fonts"
  ${else}
    StrCpy $R5 "$LOCALAPPDATA\Microsoft\Windows\Fonts"
  ${endif}

  System::Call 'gdi32::RemoveFontResource(t) i ("$R5\Iosevka-Regular.ttf") .r0'
  System::Call 'gdi32::RemoveFontResource(t) i ("$R5\Iosevka-Bold.ttf") .r0'

  ${if} $installMode == "all"
    DeleteRegValue HKLM "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka (TrueType)"
    DeleteRegValue HKLM "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka Bold (TrueType)"
  ${else}
    DeleteRegValue HKCU "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka (TrueType)"
    DeleteRegValue HKCU "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "Iosevka Bold (TrueType)"
  ${endif}

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
