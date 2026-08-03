; Εγκατάσταση/απεγκατάσταση της γραμματοσειράς Iosevka ώστε οι εξαγωγές
; Word/Excel να τη βρίσκουν ως system font (το PDF την ενσωματώνει ήδη
; απευθείας, οπότε δεν το χρειάζεται). $installMode είναι "all" (per-machine,
; απαιτεί ήδη admin/UAC) ή "CurrentUser" (per-user, χωρίς admin) — βλ.
; multiUser.nsh του electron-builder.
;
; Σημείωση: DeleteRegValue/WriteRegStr θέλουν literal root key (HKLM/HKCU),
; όχι μεταβλητή — γι' αυτό οι κλάδοι all/CurrentUser επαναλαμβάνονται.

!include "WinMessages.nsh"

; Η Iosevka είναι κοινός πόρος ανάμεσα σε ExpVault (main) και ExpVault+ (v2,
; dual-install) — αυτό το ίδιο installer.nsh είναι byte-identical και στα δύο
; branches, άρα ίδιο filename/registry key name, hardcoded, όχι per-appId.
; Χωρίς έλεγχο, το uninstall του ενός θα έσβηνε τη γραμματοσειρά ακόμα κι αν
; το άλλο είναι ακόμα εγκατεστημένο και τη χρειάζεται για εξαγωγές Word/Excel.
;
; ${SIBLING_UNINSTALL_GUID} είναι το registry uninstall subkey name που το
; electron-builder παράγει για το ΑΛΛΟ appId — UUID v5 πάνω στο appId με το
; σταθερό namespace του electron-builder
; (app-builder-lib/out/targets/nsis/NsisTarget.js: ELECTRON_BUILDER_NS_UUID =
; "50e065bc-3134-11e6-9bab-38c9862bdaf3"). Αν ποτέ αλλάξει κάποιο από τα δύο
; appId (gr.latomeio.expvault / gr.latomeio.expvaultplus), πρέπει να
; ξαναϋπολογιστεί: node -e με builder-util-runtime's UUID.v5(appId, ns).
!if "${APP_ID}" == "gr.latomeio.expvault"
  !define SIBLING_UNINSTALL_GUID "970d96d5-f888-5b28-90ac-b1f531895bf6" ; ExpVault+
  !define SIBLING_DIR_NAME "ExpVault+"
  !define SIBLING_EXE_NAME "ExpVault+.exe"
!else
  !define SIBLING_UNINSTALL_GUID "286787d3-9119-5352-8f54-2a649782d2b8" ; ExpVault
  !define SIBLING_DIR_NAME "ExpVault"
  !define SIBLING_EXE_NAME "ExpVault.exe"
!endif

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
  ; Το "αδερφό" πρόγραμμα μπορεί να είναι εγκατεστημένο σε διαφορετικό
  ; installMode από αυτό — έλεγξε και HKLM και HKCU, ανεξάρτητα από το δικό
  ; μας $installMode.
  StrCpy $R6 ""
  ReadRegStr $R6 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SIBLING_UNINSTALL_GUID}" "DisplayName"
  ${if} $R6 == ""
    ReadRegStr $R6 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SIBLING_UNINSTALL_GUID}" "DisplayName"
  ${endif}

  ; Fallback αν δεν βρέθηκε registry uninstall entry (π.χ. GUID scheme που
  ; άλλαξε σε μελλοντική έκδοση electron-builder, ή explicit "guid" override
  ; στο nsis config) — έλεγξε απευθείας τους προεπιλεγμένους φακέλους
  ; εγκατάστασης (per-machine/per-user). Δεν πιάνει custom install directory,
  ; αλλά είναι σαφώς καλύτερο από τίποτα. Το SetRegView 64 του
  ; check64BitAndSetRegView (electron-builder's uninstaller.nsh, τρέχει στο
  ; un.onInit πριν από customUnInstall) εξασφαλίζει ότι το ReadRegStr HKLM
  ; παραπάνω διαβάζει το σωστό (όχι WOW6432Node-redirected) registry view.
  ${if} $R6 == ""
    IfFileExists "$PROGRAMFILES64\${SIBLING_DIR_NAME}\${SIBLING_EXE_NAME}" sibling_found_dir 0
    IfFileExists "$LOCALAPPDATA\Programs\${SIBLING_DIR_NAME}\${SIBLING_EXE_NAME}" sibling_found_dir sibling_check_done
    sibling_found_dir:
      StrCpy $R6 "${SIBLING_DIR_NAME} (βρέθηκε στον φάκελο εγκατάστασης)"
    sibling_check_done:
  ${endif}

  ${if} $R6 != ""
    DetailPrint "Η Iosevka παραμένει εγκατεστημένη — τη χρησιμοποιεί ακόμα το $R6"
  ${else}
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
  ${endif}
!macroend

!macro customInstall
  DetailPrint "Εγκατάσταση γραμματοσειράς Iosevka..."
  !insertmacro installIosevkaFont
!macroend

!macro customUnInstall
  !insertmacro uninstallIosevkaFont
!macroend
