#!/bin/bash


species="$1"
log_path="$2"

echo ${species}
echo "-----------"




echo ${anti}
if [ ${species} == 'Mycobacterium_tuberculosis' ]
then
 h_value=0.99

elif   [ ${species} == 'Neisseria_gonorrhoeae' ]
then
#       echo ${species}
   h_value=0.98

else
   h_value=0.9
fi

cat ${log_path}log/software/AytanAktug/software_output/SSMA/${species}/cluster/temp/all_strains_assembly.txt | \
kma_clustering -i -- -k 16 -Sparse - -ht ${h_value} -hq ${h_value} -NI \
-o ${log_path}log/software/AytanAktug/software_output/SSMA/${species}/cluster/temp/clustered_90 &> \
${log_path}log/software/AytanAktug/software_output/SSMA/${species}/cluster/clustered_90.txt



