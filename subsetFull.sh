@set PRODUCT_INDEX=%3

:STATE_CONTINUE
@ECHO ".................................................."
@ECHO CURRENT PRODUCT : %PRODUCT_INDEX%
start /WAIT /b python Neural_Terra-i_Subsetting.py %1 %2 %PRODUCT_INDEX%
@SET /p PRODUCT_INDEX=<product.txt
@if not %PRODUCT_INDEX% == -1 goto STATE_CONTINUE
@ECHO ".................................................."
@ECHO SUBSETTING DONE