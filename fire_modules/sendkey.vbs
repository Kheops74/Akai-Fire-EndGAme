Set WshShell = CreateObject("WScript.Shell")

arg = WScript.Arguments(0)
sepPos = InStr(arg, "|")

If Left(arg, 7) = "__SEQ__" And sepPos > 0 Then
    arg = Mid(arg, sepPos + 1)
End If

Select Case UCase(arg)
    Case "__VK_CTRL__"
        SendVirtualKey 17
    Case "__VK_SHIFT__"
        SendVirtualKey 16
    Case "__VK_ALT__"
        SendVirtualKey 18
    Case Else
        WshShell.SendKeys arg
End Select

Sub SendVirtualKey(vk)
    cmd = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command " & _
        Chr(34) & _
        "$signature='[DllImport(" & Chr(34) & "user32.dll" & Chr(34) & ")] public static extern void keybd_event(byte bVk, byte bScan, int dwFlags, int dwExtraInfo);'; " & _
        "Add-Type -MemberDefinition $signature -Name NativeMethods -Namespace Win32; " & _
        "[Win32.NativeMethods]::keybd_event(" & vk & ",0,0,0); " & _
        "Start-Sleep -Milliseconds 40; " & _
        "[Win32.NativeMethods]::keybd_event(" & vk & ",0,2,0)" & _
        Chr(34)

    WshShell.Run cmd, 0, True
End Sub
