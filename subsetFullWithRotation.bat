@SET PRODUCT_INDEX=%4
@SET BAND_INDEX=%5

:STATE_CONTINUE
@ECHO .............
....................................
@ECHO CURRENT PRODUCT : %PRODUCT_INDEX%
@ECHO CURRENT BAND    : %BAND_INDEX%
start /WAIT /b python Neural_Terra-i_SubsettingWithRotation.py %1 %2 %3 %PRODUCT_INDEX% %BAND_INDEX%
@SET /p PRODUCT_INDEX=<product.txt
@SET /p BAND_INDEX=<band.txt
@if not %PRODUCT_INDEX% == -1 goto STATE_CONTINUE
@ECHO ..................................................
@ECHO SUBSETTING DONE