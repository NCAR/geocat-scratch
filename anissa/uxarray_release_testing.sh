#/bin/zsh

# run with `zsh -i uxarray_release_testing.sh`

# Remove environment if it already exists
yes | mamba remove -n script_ux_release_test --all

# Make an empty conda environment
yes | mamba create -n script_ux_release_test -c conda-forge uxarray

# Activate the environment
conda activate script_ux_release_test

# Print conda environment and save to log file with package name and date time
conda list > "ux_"$(date +%Y-%m-%d)".log"
conda list

# Import package and capture output to log file
echo "\n\nImport UXarray\n------------------" >> "ux_"$(date +%Y-%m-%d)".log"
python -uc "import uxarray; print(uxarray.__version__)" 2>&1 | tee -a "ux_"$(date +%Y-%m-%d)".log"

# Deactivate the environment
conda deactivate

# Remove the environment
yes | mamba remove -n script_ux_release_test --all
