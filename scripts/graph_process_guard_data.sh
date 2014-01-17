#!/bin/bash
# graph_process_guard_data.sh ---
#
# Filename: graph_process_guard_data.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Dec  2 18:54:21 2013 (+0100)

# Commentary:
# %*% This script will generate all the resource usage graphs from process_guard.py's output files found in OUTPUT_DIR.
#
#
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code:

# Check that $OUTPUT_DIR exists to avoid going to hour home dir by accident.
if [ -z "$OUTPUT_DIR" ]; then
    echo 'ERROR: $OUTPUT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

cd $OUTPUT_DIR

extract_process_guard_stats.py . .
reduce_dispersy_statistics.py . 300

#Create the graphs
mkdir -p $R_LIBS_USER
R --no-save --quiet < $R_SCRIPTS_PATH/install.r
R --no-save --quiet < $R_SCRIPTS_PATH/cputimes.r 2>&1 > /dev/null
R --no-save --quiet < $R_SCRIPTS_PATH/memtimes.r 2>&1 > /dev/null


#
# graph_process_guard_data.sh ends here
