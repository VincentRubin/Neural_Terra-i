#!/usr/bin
PRODUCT_INDEX=$3

while [PRODUCT_INDEX -gt -1]
do
	echo ".................................................."
	echo "CURRENT PRODUCT : " + $PRODUCT_INDEX
	python Neural_Terra-i_Subsetting.py $1 $2 $PRODUCT_INDEX
	PRODUCT_INDEX=$(head -n 1 product.txt)
	echo ".................................................."
done
echo "SUBSETTING DONE"