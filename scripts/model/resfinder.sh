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
export PATH=$( dirname $( dirname $( which conda ) ) )/bin:$PATH
export PYTHONPATH=$PWD

echo $CONDA_DEFAULT_ENV
IFS=', ' read -ra species_list_temp <<< "$species_list"
species=( "${species_list_temp[@]//_/ }" )
IFS=', ' read -ra species_list_temp_tree <<< "$species_list_phylotree"
species_tree=( "${species_list_temp_tree[@]//_/ }" )





source activate ${resfinder_env}
wait
echo "Point-/Resfinder blastn version:"
python ./AMR_software/resfinder/main_run_blastn.py -path_sequence ${dataset_location} -temp ${log_path} --n_jobs ${n_jobs} -s "${species[@]}" -l ${QC_criteria} || { echo "Errors in resfinder running. Exit ."; exit; }

echo "Point-/Resfinder KMA version:"
python ./AMR_software/resfinder/main_run_kma.py -path_sequence ${dataset_location} -temp ${log_path} --n_jobs ${n_jobs} -s "${species[@]}" -l ${QC_criteria} || { echo "Errors in resfinder running. Exit ."; exit; }

source activate ${amr_env_name}
echo "Point-/Resfinder extract results:"
python ./AMR_software/resfinder/extract_results.py -s "${species[@]}" -f_no_zip -o ${output_path} -temp ${log_path} || { echo "Errors in resfinder results summarize. Exit ."; exit; }
conda deactivate


#### Evaluate resfinder under CV folds

echo "Evaluate Point-/Resfinder under CV folds:"
python ./AMR_software/resfinder/main_resfinder_folds.py -f_phylotree -cv ${cv_number} -temp ${log_path} -s "${species_tree[@]}" -l ${QC_criteria}  -f_no_zip|| { echo "Errors in resfinder running. Exit ."; exit; }
python ./AMR_software/resfinder/main_resfinder_folds.py -f_kma -cv ${cv_number} -temp ${log_path} -s "${species[@]}" -l ${QC_criteria}  -f_no_zip|| { echo "Errors in resfinder running. Exit ."; exit; }
python ./AMR_software/resfinder/main_resfinder_folds.py -cv ${cv_number} -temp ${log_path} -s "${species[@]}" -l ${QC_criteria}  -f_no_zip|| { echo "Errors in resfinder running. Exit ."; exit; }


### CV score generation.
python ./src/analysis_utility/result_analysis.py -software 'resfinder_folds' -f_phylotree -cl_list 'resfinder' -cv ${cv_number} -temp ${log_path} -o ${output_path} -s "${species_tree[@]}" -l ${QC_criteria}
python ./src/analysis_utility/result_analysis.py -software 'resfinder_folds' -f_kma  -cl_list 'resfinder'  -cv ${cv_number} -temp ${log_path} -o ${output_path} -s "${species[@]}" -l ${QC_criteria}
python ./src/analysis_utility/result_analysis.py -software 'resfinder_folds'  -cl_list 'resfinder' -cv ${cv_number} -temp ${log_path} -o ${output_path} -s "${species[@]}" -l ${QC_criteria}
conda deactivate

echo "Point-/Resfinder finished successfully."
