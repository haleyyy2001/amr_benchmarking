**Python 2.7** conda environment called `kover-env`. 

---

# README: Setting Up the Kover Environment (kover-env)

This document describes how to create and configure a conda environment, named **kover-env**, for running **Kover** (2.0) on your HPC system. It covers installing Python 2.7, ensuring MultiDSK is properly available in `PATH`, and troubleshooting common setup issues we encountered in our AMR benchmarking.

---

## 1. Create and Activate the Conda Environment

1. **Load any necessary HPC modules** (if your cluster uses environment modules). Often you might run:
   ```bash
   module load anaconda3/2022.10
   ```
   or a similar command, depending on your system.

2. **Create** the `kover-env` environment with Python 2.7:
   ```bash
   conda create -n kover-env python=2.7 -y
   ```
3. **Activate** it:
   ```bash
   conda activate kover-env
   ```
4. Verify you’re in Python 2.7:
   ```bash
   python --version
   # Should print something like: Python 2.7.x
   ```

---

## 2. Install Kover and Dependencies

### 2.1 Kover 2.0

If you have a local clone of the Kover repo, navigate to it and run:
```bash
python setup.py install
```
or install via pip if available:
```bash
pip install kover==2.0
```
*(Check the exact version or local tarball instructions if you have them.)*

**Alternatively**, if your HPC environment includes a custom build of Kover you can use, just confirm the relevant `kover.py` is accessible in your environment’s `PATH`.

### 2.2 MultiDSK and KMC

Kover relies on external tools (MultiDSK and KMC or similar) for k-mer counting:

1. **MultiDSK**:  
   - Confirm it’s installed in your environment:
     ```bash
     which multidsk
     ```
   - If not found, install it or place it in `kover-env/bin`. One approach is to download MultiDSK from its repository (if a precompiled binary is provided), then copy that binary into:
     ```
     /burg/pmg/users/ht2666/mambaforge/envs/kover-env/bin/
     ```
   - Finally, verify:
     ```bash
     multidsk --help
     ```
     should print usage info.

2. **KMC** (optional if you use it in some Kover subcommands):
   ```bash
   conda install -c bioconda kmc
   ```

---

## 3. Confirm the Setup

When you run `kover.py`, Kover checks for:
1. **MultiDSK** in your `PATH`.  
2. The correct Python 2.7 environment with `kmer_pack`, `kmer_count`, and other submodules installed.

Run:
```bash
which python
python -c "import kover; print(kover.__file__)"
which multidsk
multidsk --help
```
All these commands should point to paths inside `kover-env/bin` or the site-packages of `kover-env`.

---

## 4. Common Issues & Troubleshooting

1. **`ImportError: No module named kmer_pack` or `kmer_count`**  
   - Means Kover’s internal Python modules aren’t fully installed. Re-run:
     ```bash
     cd /path/to/Kover/
     python setup.py install
     ```
     inside `kover-env`.

2. **`RuntimeError: [ERROR] MultiDSK binary not found in PATH!`**  
   - Even if you see “Found MultiDSK at …” in partial logs, HPC environment changes can break your `PATH`. Fix by placing MultiDSK in `kover-env/bin` and confirming with:
     ```bash
     which multidsk
     ```

3. **`IOError: Cannot send after transport endpoint shutdown`**  
   - Typically an HPC filesystem issue or NFS glitch. Retry once the filesystem is stable. Not an environment problem per se, but can halt Kover runs mid-way.

4. **`LookupError: unknown encoding: string-escape`**  
   - Usually a mismatch between Python 2 and system locales. Make sure you’re truly in Python 2.7 and have standard locales set:
     ```bash
     export LANG=en_US.UTF-8
     export LC_ALL=en_US.UTF-8
     ```
   - Double-check you’re not mixing Python 3 environment variables.

---

## 5. Integrating with HPC Job Scripts

Many HPC job scripts look like:
```bash
#!/bin/bash
#SBATCH --job-name=kover_job
#SBATCH --time=48:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --output=/path/to/log/kover_out_%j.log
#SBATCH --error=/path/to/log/kover_err_%j.log

module load anaconda3/2022.10  # or whichever module
conda activate kover-env

# Verify environment
which python
which multidsk
kover.py --help

# Run your Kover command(s)
kover.py dataset create from-contigs ...
kover.py learn scm --dataset ...
# ...
```
Ensure you:

1. **Activate `kover-env`** early in the script.  
2. Confirm HPC or Slurm sees the right `PATH` and environment variables.

---

## 6. Memory and Disk Considerations

- **Kover** can generate large intermediate files (especially for big datasets with millions of k-mers).  
- Ensure you request enough memory (`--mem=XXG`) in Slurm.  
- Clean up after runs, especially if your HPC scratch space is limited.

---

## 7. Final Check

Once you finish, try a small test dataset. If it completes with no errors and you see correct Kover output (e.g., a “Kover Learning Report” with metrics), your environment is set up correctly.

---

### Questions / Contact

If you have further issues or environment conflicts, refer back to your HPC docs or the Kover GitHub issues. For local HPC questions, email the cluster support or check with your lab’s HPC admin. 

**Congratulations!** You now have a fully functional `kover-env` environment. You can proceed to run the AMR benchmarking scripts that call Kover.
