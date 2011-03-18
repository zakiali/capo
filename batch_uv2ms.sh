#$ -S /bin/bash
#$ -N casa_uv2ms
#$ -j y
#$ -o grid_output/
#$ -V
#$ -cwd

CAL=psa455_v004_gc
ARGS=`pull_args.py $*`
echo casapy --logfile grid_output/casalog_bash_uv2ms_${JOB_ID}_${TASK_ID}.log --nologger -c bash_uv2ms.py -C ${CAL} ${ARGS}
casapy --logfile grid_output/casalog_bash_uv2ms_${JOB_ID}_${TASK_ID}.log --nologger -c bash_uv2ms.py -C ${CAL} ${ARGS}
