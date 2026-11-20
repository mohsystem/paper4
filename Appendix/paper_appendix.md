# Participant-level severity profiles

Table 1 reports raw severity composition for each participant in both conditions. Its purpose is transparency; formal analysis is based on paired participant-level change scores.

## Table 1. Participant-level severity profile before and after training

C = Critical, H = High, M = Medium, L = Low, and T = Total.

| ID | Stratum | Pre C | Pre H | Pre M | Pre L | Pre T | Post C | Post H | Post M | Post L | Post T |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P01 | Senior | 1 | 5 | 0 | 1 | 7 | 0 | 4 | 0 | 1 | 5 |
| P02 | Senior | 3 | 8 | 5 | 1 | 17 | 0 | 2 | 0 | 0 | 2 |
| P03 | Senior | 0 | 7 | 4 | 2 | 13 | 1 | 7 | 6 | 1 | 15 |
| P04 | Junior | 4 | 8 | 2 | 1 | 15 | 0 | 2 | 4 | 1 | 7 |
| P05 | Junior | 1 | 10 | 3 | 1 | 15 | 2 | 6 | 0 | 3 | 11 |
| P06 | Junior | 1 | 8 | 2 | 1 | 12 | 1 | 2 | 2 | 0 | 5 |
| P07 | Junior | 3 | 4 | 2 | 1 | 10 | 1 | 5 | 3 | 0 | 9 |
| P08 | Senior | 0 | 7 | 1 | 0 | 8 | 0 | 6 | 3 | 0 | 9 |
| P09 | Senior | 3 | 7 | 2 | 3 | 15 | 0 | 6 | 5 | 0 | 11 |
| P10 | Senior | 2 | 4 | 2 | 0 | 8 | 0 | 5 | 2 | 2 | 9 |
| P11 | Junior | 0 | 3 | 7 | 3 | 13 | 0 | 0 | 2 | 3 | 5 |
| P12 | Junior | 2 | 7 | 1 | 1 | 11 | 0 | 2 | 0 | 0 | 2 |
| **Total** | **--** | **20** | **78** | **31** | **15** | **144** | **5** | **47** | **27** | **11** | **90** |

---

# Task-Set Specifications

The task-sets A and B specifications are provided in the online appendix: [Task-set specifications](https://github.com/mohsystem/paper4/blob/master/Appendix/appendix_task_set_specifications.md).

## CWE-to-Weakness-Family Mapping

To support the descriptive domain-level analysis in Table 2, each CWE was assigned to a single researcher-defined weakness family. The mapping reflects recurring security concerns in identity-centric backends while reducing fragmentation across low-frequency CWEs.

## Table 2. CWE-to-weakness-family mapping used for the domain-level analysis

| Weakness family | CWE identifiers |
|:---|:---|
| Authorization & object access | CWE-269, CWE-639, CWE-732, CWE-807, CWE-862 |
| Authentication, credential policy & recovery | CWE-258, CWE-259, CWE-287, CWE-306, CWE-521, CWE-522, CWE-523, CWE-640, CWE-798, CWE-916 |
| Session, request & browser trust boundary | CWE-352, CWE-384, CWE-613, CWE-1021 |
| Sensitive data, secrets & cryptography | CWE-201, CWE-312, CWE-319, CWE-321, CWE-330, CWE-338 |
| Logging, errors & information exposure | CWE-117, CWE-203, CWE-204, CWE-209, CWE-532, CWE-778 |
| Configuration & debug surface | CWE-489 |
| Input validation & unsafe integration | CWE-20, CWE-611, CWE-90, CWE-918 |
| Availability & abuse resistance | CWE-307, CWE-400 |
| File handling | CWE-434 |
