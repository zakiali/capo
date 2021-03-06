#$ -S /bin/bash
#$ -V
#$ -cwd
#$ -o grid_output
#$ -j y
#$ -l h_vmem=18G
#$ -N LSTBIN
export PATH=/home/jacobsda/src/anaconda/bin:$PATH
#source activate PAPER
source activate OMNI2
LSTS=`python -c "import numpy as n; hr = 1.0; print ' '.join(['%f_%f' % (d,d+hr/4.) for d in n.arange(0,23.999*hr,hr/4.)])"`
#LSTS=`python -c "import numpy as n; hr = 1.0; print ' '.join(['%f_%f' % (d,d+hr/4.) for d in n.arange(6,9*hr,hr/4.)])"`
#LSTS=`python -c "import numpy as n; hr = 1.0; print ' '.join(['%f_%f' % (d,d+hr/4.) for d in n.arange(5.25,9.5*hr,hr/4.)])"`
#LSTS=9.250000_9.500000
MY_LSTS=`~/src/capo/dcj/scripts/pull_args.py $LSTS`
CALFILE=psa6622_v002
PREFIX=lstbin_19Jan2016_v1

echo $MY_LSTS
echo mkdir ${PREFIX}
mkdir ${PREFIX}
cd ${PREFIX}
for LST in $MY_LSTS; do
    echo Working on $LST
    echo working on even files
    MYFILES=`python ~/scripts/select_file_parity.py $*`
    MYFILES=`lst_select.py --ra=${LST} --suntime=n -C ${CALFILE} ${MYFILES}`
    echo data volume: $(du -csh $MYFILES)
    mkdir even
    cd even
    echo ~/src/capo/scripts/lstbin_v02.py -a cross -C ${CALFILE} --lst_res=42.95 --lst_rng=$LST \
    --tfile=600 --altmax=0 --stats=all --median --nsig=3 `python ~/scripts/select_file_parity.py $*`
    python ~/src/capo/scripts/lstbin_v02.py -a cross -C ${CALFILE}  --lst_res=42.95 --lst_rng=$LST \
    --tfile=600 --altmax=0 --stats=all --median --nsig=3 `python ~/scripts/select_file_parity.py $*`
    cd ..

    echo working on odd files
    mkdir odd
    cd odd
    echo /usr/global/paper/capo/scripts/lstbin_v02.py -a cross -C ${CALFILE} -s Sun --lst_res=42.95 --lst_rng=$LST \
    --tfile=600 --altmax=0 --stats=all --median --nsig=3 `python ~/scripts/select_file_parity.py $*`
    python ~/src/capo/scripts/lstbin_v02.py -a cross -C ${CALFILE} --lst_res=42.95 --lst_rng=$LST \
    --tfile=600 --altmax=0 --stats=all --median --nsig=3 `python ~/scripts/select_file_parity.py --odd $*`
    cd ..

done;
