sc stop GAppProxy
sc delete GAppProxy
sc create GAppProxy binPath= "%~dp0srvany.exe" start= auto
sc description GAppProxy "HTTP ������� - GAppProxy Ϊ��Ч�͡�"
reg add HKLM\SYSTEM\CurrentControlSet\Services\GAppProxy\Parameters /v Application /d "%~dp0..\proxy.exe" /f
reg add HKLM\SYSTEM\CurrentControlSet\Services\GAppProxy\Parameters /v AppDirectory /d "%~dp0..\" /f
sc start GAppProxy
::@echo.
::@echo ��װ����ɣ�GAppProxy �����Ѿ�������
::@echo.
::@echo �����Թر�������ڣ���ʼʹ�ô����ˡ�
::@echo.
::@echo Enjoy it :-)
::@echo.
::@pause