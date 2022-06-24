## Suites
suites are used to provide data related to run test suites.

| Folders | Description |
| ------- | ----------- |
| `misc` | Definition for test suites which would be uniform across.|
| `rbd` | Definition for test suites for rbd operations. |
| `rgw` | placeholder for test suites for rgw operations. |

## Guidelines
- Use lowercase for filenames separated either by `-` or `_`.
- Use `.yaml` as the file extension instead of `.yml`
- Ensure the file follows YAML best practices.
- Use `_` to have a separation of category.
- Use soft links instead of copying files between folders.
- Create folders for every component.
- One test case definition per file.
- The name of the file is descriptive.
- Each test case has a top level description.
- Keep a linear structure.
- Use cluster_name.test_name.step_number in key:load_input_result if you want to access any variable from one cluster to another cluster.
- Use component name(ceph/cephadm/rados/rbd/radosgw-admin) as component, feature name(word before an operation) as method, operation name as method
    in test suite.yaml
