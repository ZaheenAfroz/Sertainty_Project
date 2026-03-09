# Supplementary Materials for "Enhanced Security of Bidirectional Communication in IoT-Driven Utility Networks Using Sertainty UXP and LoRaWAN"

This repository contains the supplementary scripts used in support of the study:

**Enhanced Security of Bidirectional Communication in IoT-Driven Utility Networks Using Sertainty UXP and LoRaWAN**

## Overview

This study investigates the feasibility of applying additional application-layer security to LoRaWAN-based IoT utility networks. In particular, it evaluates the performance and overhead of multiple encryption approaches, including:

- AES-256-GCM
- ASCON-128
- SPECK
- XTEA
- Sertainty UXP
- Unencrypted baseline

The main objective is to examine how these approaches affect secure bidirectional communication over LoRaWAN under payload and performance constraints. The evaluation considers factors such as latency, payload handling, message transmission, and end-to-end processing across the LoRaWAN architecture.

## Repository Purpose

This repository is provided as supplementary material to support reproducibility and implementation transparency for the experimental workflow described in the paper. The scripts included here were used for encryption-related preprocessing, payload preparation, transmission-side handling, reception-side handling, and associated utility functions.

## Folder Structure

- `AES-256_scripts/`  
  Scripts related to AES-256-GCM encryption, payload generation, transmission, and post-processing.

- `ASCON_scripts/`  
  Scripts used for ASCON-128-based encryption and related LoRaWAN transmission workflow.

- `misc/`  
  Miscellaneous helper scripts, utilities, or intermediate support code used during experimentation.

- `sertainty_script/`  
  Scripts associated with the Sertainty UXP-based data protection workflow, including preparation, protection, splitting, joining, and related processing steps.

- `SPECK_scripts/`  
  Scripts implementing or evaluating the SPECK-based workflow.

- `Unencrypted_script/`  
  Scripts used for baseline transmission without additional application-layer encryption.

- `XTEA_scripts/`  
  Scripts implementing or evaluating the XTEA-based workflow.

## Experimental Context

The scripts support an experimental setup in which smart meter data were preprocessed, optionally encrypted, transmitted over a LoRaWAN architecture, received through the network stack, and then logged or reconstructed for analysis. The study compares encrypted and unencrypted workflows to evaluate the communication cost of stronger application-layer protection in resource-constrained IoT environments.

## Notes

- These scripts are shared as supplementary research material.
- Some scripts may depend on specific hardware, software environments, LoRaWAN settings, external services, or proprietary tools used in the original experimental setup.
- Sertainty UXP-related operations may require access to proprietary components not included in this repository.
- Users may need to adapt file paths, credentials, device parameters, and runtime settings to reproduce the workflow in a different environment.

## Citation

If you use this repository, please cite the associated paper.

## Disclaimer

This repository is intended for academic and research purposes only. It is provided to document the experimental workflow associated with the study and to improve transparency of the implementation.
