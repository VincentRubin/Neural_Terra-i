List of python dependencies (PYTHON 3.6) :

sentinelsat
glob
zipfile36
gdal
rasterio
fiona
geojson
glob2
numpy
pytest-shutil
base conda
matplotlib

Install the dependencies with the script conda_install_needs.bat or create a new conda environment with the file conda_environment.yml.

Scripts : Windows : In a command line prompt, activate the wanted conda env then start the .bat. 
	  (Neural_Terra-i work with Python 3.6)

	conda create -n python36 python=3.6.13
	conda activate python36
	conda_install_needs.bat

Use the yml file : conda env create -f conda_environment.yml