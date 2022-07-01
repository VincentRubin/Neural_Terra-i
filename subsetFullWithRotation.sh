PRODUCT_INDEX=$4
BAND_INDEX=$5

while [$PRODUCT_INDEX -gt -1]
do
	echo .................................................
	echo "CURRENT PRODUCT : " $PRODUCT_INDEX
	echo "CURRENT BAND    : " $BAND_INDEX
	python Neural_Terra-i_SubsettingWithRotation.py $1 $2 $3 $PRODUCT_INDEX $BAND_INDEX
	PRODUCT_INDEX=$(head -n 1 product.txt)
	BAND_INDEX=$(head -n 1 band.txt)
	@if not %PRODUCT_INDEX% == -1 goto STATE_CONTINUE
	echo ..................................................
done
echo SUBSETTING DONE