#!/bin/bash

function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}
eval $(parse_yaml Config.yaml)

export PATH="$PWD"/src:$PATH
export PYTHONPATH=$PWD
SCRIPT=$(realpath "$0")
SCRIPTPATH=$(dirname "$SCRIPT")
################################################
#PART 1. Install 7 pieces of conda environments
################################################
### note: if you use GPU for NN model, you need to install pytorch in the multi_torch_env env.
### To install pytorch compatible with your CUDA version, please fellow this instruction: https://pytorch.org/get-started/locally/.
### Our code was tested with pytorch v1.7.1, with CUDA Version: 10.1 and 11.0 .
#
bash ./install/install.sh
echo "Please check if Env created."
#-------------------------------------------
#2.PATRIC Data
#-------------------------------------------
#Download  PATRIC_genomes_AMR.txt from https://docs.patricbrc.org/user_guides/ftp.html on Dec. 2020.
#Download quality attribute tables using p3-all-genomes, saved at : ./data/PATRIC/quality/${species}.csv, for quality control(QC).
#Based on above mentioned materials, we conducted a pre-selection(selecion based only on sample numbers w.r.t. each species) and QC, and then downloaded the data based on the pre-selection.
# We use the dataset based on QC.

#2.0 Quality control  (You can skip this step, as we provided the sample list after pre-selection &  QC: ./data/PATRIC/meta)
## If you want to go through the pre-selection & QC, and re-generate the list. Note: this step will update the ./data/PATRIC/meta folder.
bash ./scripts/data/preprocess.sh

# 2.1 PATRIC Data download
bash ./scripts/data_preprocess/retrive_PATRIC_data.sh ${dataset_location}




##############################
#2. Software 1. Point-/Resfinder
##############################
#optional: Blastn-based version can be installed from https://bitbucket.org/genomicepidemiology/resfinder/src/master/
#origianl KMA-based version can only process read data(FASTQ files).
# Here we provided the modified version of KMA-based Point-/Resfinder that can use genomic data. This is done because NN multi-species model (Aytan-Aktug et al.)
# can only be generated by KMA-based Point-/Resfinder.
#reference database version 2021-05-06. You can also update the ref database (hopefully will get better performance.)

### install KMA and Point-/Resfinder
##If issues arise in this step, you can alternatively manually install it.
## please further refer to https://bitbucket.org/genomicepidemiology/resfinder/src/master/

cd ./AMR_software/resfinder
cd cge
git clone https://bitbucket.org/genomicepidemiology/kma.git
cd kma && make
cd SCRIPTPATH

#index Point-/ResFinder databases with KMA
cd ./AMR_software/resfinder/db_resfinder
python3 INSTALL.py ${BASEDIR}/AMR_software/resfinder/cge/kma/kma non_interactive
cd $BASEDIR
cd ./AMR_software/resfinder/db_pointfinder
python3 INSTALL.py ${BASEDIR}/AMR_software/resfinder/cge/kma/kma non_interactive
cd SCRIPTPATH

bash /scripts/model/resfinder.sh






##############################
###4. Software 2. Aytan-Aktug. Adaption version.
###Note: SSSA model support both CPU parallelization running and GPU sequential running. (via gpu_on in Config.yaml)
### Other 4 multi- models are designed only for GPU running due to heavy computing load (although it can still run on CPU machines without needing to to anything.).
### You can further tear each of them into smaller running jobs by assigning i and j variables to a specific value within the range specified in each corresponding script.
### an example of tearing to smaller tasks is explained in 4.2 ./scripts/model/AytanAktug_SSMA.sh script.
### note: 4.4 and 4.5 are based on some intermediate feature files from 4.3, so please run the 3 multi-species models feature generation part sequentially.
##Reference: Early stopping for PyTorch https://github.com/Bjarten/early-stopping-pytorch
##############################

# 4.1 single-species single-antibiotics
bash ./scripts/model/AytanAktug_SSSA.sh

# 4.2 single-species multi-antibiotics
bash ./scripts/model/AytanAktug_SSMA.sh

# 4.3 discrete databases multi-species model
bash ./scripts/model/AytanAktug_MSMA_discrete.sh

# 4.4 concatenated databases mixed(-species) multi-species model
# 4.5  concatenated databases leave-one(-species)-out multi-species model
bash ./scripts/model/AytanAktug_MSMA_concat.sh




##############################
#5. Software 3.Seq2Geno
##############################
## set up snakemake pipeline.
cd SCRIPTPATH
cd ./AMR_software/seq2geno/install/
./SETENV.sh ${se2ge_env_name}
export PATH=$( dirname $( dirname $( which conda ) ) )/bin:$PATH
export PYTHONPATH=$PWD
conda activate ${se2ge_env_name}
./TESTING.sh
conda deactivate
# Then update seq2geno to the adaption version that can deal with genome data
cd SCRIPTPATH
cd ./AMR_software/
cp  -r seq2geno_assemble/* seq2geno/
wait
bash ./scripts/model/seq2geno.sh #Run.
echo "Features are prepared, please then proceed to https://galaxy.bifo.helmholtz-hzi.de/galaxy/root?tool_id=genopheno to run Geno2Pheno"
##### CV score generation. Not provided because Geno2Phen is not an open source software.
#bash ./scripts/model/seq2geno.sh #Run results from Geno2Pheno. Please manually uncomment the the CV score generation part Line 70-84, and comment other already-finished parts.
##The Geno2Pheno output format is different

##############################
#6. Software 4. Phenotyperseeker
##############################
bash ./scripts/model/phenotypeseeker.sh


##############################
#7. Software 5. Kover
##############################
## Please install Kover 2.0 according to https://aldro61.github.io/kover/doc_installation.html or https://github.com/aldro61/kover
## We used the command line version in Linux.
bash ./scripts/model/kover.sh

##############################
#7. Software 6. ML baseline (majority)
##############################
bash ./scripts/model/majority.sh



#-------------------------------------------
#8. Main Analysis and Visualiztion
#-------------------------------------------
bash ./scripts/analysis_visualization/AytanAktug_analysis.sh
bash ./scripts/analysis_visualization/compare.sh


#-------------------------------------------
#9. Other Visualiztion(supplements)
#-------------------------------------------
bash ./scripts/analysis_visualization/compare_supplement.sh





echo "Please find the results(tables, figures, and statistic numbers mentioned at the AMR benchmarking article) at the location set by Config.yaml
.
└── Results
    ├── final_figures_tables
    ├── other_figures_tables
    ├── supplement_figures_tables
    └── software
         │── AytanAktug
         ├── kover
         ├── resfinder_b
         ├── resfinder_folds
         ├── resfinder_k
         └── seq2geno

"


