
# README: Setting Up the Kover Environment (kover-env)

This document describes how to create and configure a conda environment named **kover-env**, using **Python 2.7**, for running **Kover** (2.0+) on an HPC system. It also covers installing core dependencies like **MultiDSK** (or **KMC**) and includes troubleshooting pointers.

---

## 1. Load HPC Modules (If Applicable)

Depending on your HPC setup, you may need to load an Anaconda/conda module first. For example:
```bash
module load anaconda3/2022.10
```
*(Adjust module name/version as needed. Some systems may provide `mamba` instead.)*

---

## 2. Create and Activate the Python 2.7 Environment

1. **Create** a new conda environment called `kover-env`:
   ```bash
   conda create -n kover-env python=2.7 -y
   ```
   Alternatively, you can install to a fixed path if you prefer:
   ```bash
   conda create --prefix /burg/pmg/users/ht2666/mambaforge/envs/kover-env python=2.7 -y
   ```

2. **Activate** the newly created environment:
   ```bash
   conda activate kover-env
   ```
   or, if using a specific prefix:
   ```bash
   conda activate /burg/pmg/users/ht2666/mambaforge/envs/kover-env
   ```

3. **Verify** the Python version:
   ```bash
   python --version
   # Should print: Python 2.7.x
   ```

---

## 3. Install Kover and Required Dependencies

### 3.1 Install Kover

There are multiple ways to install Kover 2.0.x:

- **From a local clone**:  
  ```bash
  cd /path/to/kover-source/
  python setup.py install
  ```
- **From a (custom) conda channel or PyPI** (if available):  
  ```bash
  pip install kover==2.0
  ```
  *(Adjust the version/tag if needed.)*

### 3.2 Install/Check External Tools (MultiDSK or KMC)

Kover relies on external k-mer counting tools:

- **KMC**  
  ```bash
  conda install -c bioconda kmc
  ```
  This should place the `kmc` binary in your active environment’s PATH.

- **MultiDSK**  
  Some Kover pipelines may require MultiDSK:
  1. Confirm it’s installed:
     ```bash
     which multidsk
     ```
     If not found, you can install or copy a precompiled binary into:
     ```
     /burg/pmg/users/ht2666/mambaforge/envs/kover-env/bin/
     ```
  2. Test it:
     ```bash
     multidsk --help
     ```
     should display usage info.

---

## 4. Verifying the Setup

Once installed, confirm that Kover and the related utilities are accessible in your environment:

```bash
# Check Python location
which python
python --version

# Check Kover’s import
python -c "import kover; print(kover.__file__)"

# Check MultiDSK or KMC
which multidsk
multidsk --help
which kmc
kmc --help
```

All paths should point to your `kover-env` environment (e.g., `.../kover-env/bin/` or site-packages under `kover-env`).

---

## 5. Export or Share the Environment (Optional)

To help collaborators replicate the exact environment, you can export it to a YAML file:

```bash
conda env export --prefix /burg/pmg/users/ht2666/mambaforge/envs/kover-env > kover-env.yml
```
They can recreate the same environment by running:
```bash
conda env create -f kover-env.yml
```

---

## 6. Using Kover in HPC Job Scripts

A typical Slurm job script might look like this:

```bash
#!/bin/bash
#SBATCH --job-name=kover_job
#SBATCH --output=/path/to/logs/kover_out_%j.log
#SBATCH --error=/path/to/logs/kover_err_%j.log
#SBATCH --time=48:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16

module load anaconda3/2022.10   # or whichever module needed
conda activate kover-env        # or the full path to your env

# Verify environment
which python
python --version
which kover.py  # or however Kover is called
which multidsk  # or kmc
kover.py --help

# Run your Kover commands
kover.py dataset create from-contigs ...
kover.py learn scm --dataset ...
...
```

---

## 7. Troubleshooting

### 7.1 Missing Kover Modules (`ImportError`)

If you see something like:
```
ImportError: No module named kmer_pack
```
- Reinstall Kover in the current Python 2.7 environment:
  ```bash
  cd /path/to/kover-source/
  python setup.py install
  ```

### 7.2 MultiDSK or KMC Not Found in `PATH`

If Kover fails with errors like “`RuntimeError: [ERROR] MultiDSK binary not found in PATH!`”:
- Ensure you have **MultiDSK** (or **kmc**) installed in the environment or in a directory recognized by PATH.
- If your HPC environment modifies `PATH` between interactive and batch modes, consider copying the `multidsk` binary into `/burg/pmg/users/ht2666/mambaforge/envs/kover-env/bin/`.

### 7.3 Encoding Errors (`unknown encoding: string-escape`)

- This is often caused by locale settings. For Python 2.7, ensure:
  ```bash
  export LANG=en_US.UTF-8
  export LC_ALL=en_US.UTF-8
  ```
- Confirm you’re actually in Python 2.7 (not 3.x) and that you’re not mixing environment variables from another environment.

### 7.4 HPC Filesystem Issues

If you see NFS or I/O-related errors (“`Cannot send after transport endpoint shutdown`”), it could be HPC filesystem congestion. Retry after ensuring your scratch directory is stable.

---

## 8. Memory and Disk Considerations

- **Kover** can generate large intermediate files, especially with big datasets.  
- Request adequate memory in your Slurm job (`--mem=XXG`) and ensure you have enough disk space in your working directory or scratch folder.  
- Clean up temporary files if your pipeline doesn’t do so automatically.

---

## 9. Final Check

1. **Activate** `kover-env`.
2. **Test** a small dataset with Kover to confirm all dependencies work and you see normal Kover output/logs (e.g., the “Kover Learning Report”).
3. **Share** your final environment or environment file (`kover-env.yml`) with collaborators to ensure reproducibility.

**Congratulations!** You have a fully functional Kover environment under Python 2.7 on your HPC system.
