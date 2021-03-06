
import pytest
from kiali_qe.tests import IstioConfigPageTest, ServicesPageTest

from kiali_qe.utils import get_yaml, get_dict
from kiali_qe.utils.path import istio_objects_path
from kiali_qe.components.enums import (
    IstioConfigObjectType,
    IstioConfigPageFilter,
    IstioConfigValidationType
)

'''
Tests are divided into groups using different services and namespaces. This way the group of tests
can be run in parallel.
'''

BOOKINFO_1 = 'bookinfo'
BOOKINFO_2 = 'bookinfo2'
REVIEWS = 'reviews'
DETAILS = 'details'
RATINGS = 'ratings'
DEST_RULE = 'destination-rule-cb-details.yaml'
DEST_RULE_VS_RATINGS = 'destination-rule-ratings.yaml'
DEST_RULE_VS_REVIEWS = 'destination-rule-reviews.yaml'
DEST_RULE_BROKEN = 'destination-rule-cb-broken.yaml'
VIRTUAL_SERVICE = 'virtual-service.yaml'
VIRTUAL_SERVICE_BROKEN = 'virtual-service-broken.yaml'
VIRTUAL_SERVICE_BROKEN_WEIGHT = 'virtual-service-broken-weight.yaml'
VIRTUAL_SERVICE_BROKEN_WEIGHT_TEXT = 'virtual-service-broken-weight-text.yaml'
QUOTA_SPEC = 'quota-spec.yaml'
QUOTA_SPEC_BINDING = 'quota-spec-binding.yaml'
GATEWAY = 'gateway.yaml'
SERVICE_ENTRY = 'service-entry.yaml'
CLUSTER_RBAC_CONFIG = 'cluster-rbac-config.yaml'
RBAC_CONFIG = 'rbac-config.yaml'
SERVICE_ROLE = 'service-role.yaml'
SERVICE_ROLE_BROKEN = 'service-role-broken.yaml'
SERVICE_ROLE_BINDING = 'service-role-binding.yaml'
SERVICE_ROLE_BINDING_BROKEN = 'service-role-binding-broken.yaml'


@pytest.mark.p_crud_resource
@pytest.mark.p_group1
def test_destination_rule(kiali_client, openshift_client, browser):
    destination_rule = get_yaml(istio_objects_path.strpath, DEST_RULE)
    destination_rule_dict = get_dict(istio_objects_path.strpath, DEST_RULE)

    _istio_config_test(kiali_client, openshift_client, browser,
                       destination_rule_dict,
                       destination_rule,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.DESTINATION_RULE.text},
                        {'name': IstioConfigPageFilter.CONFIG.text,
                         'value': IstioConfigValidationType.VALID.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': destination_rule_dict.metadata.name}
                        ],
                       namespace=BOOKINFO_1,
                       kind='DestinationRule',
                       api_version='networking.istio.io/v1alpha3',
                       service_name=DETAILS,
                       check_service_details=True)


@pytest.mark.p_crud_resource
@pytest.mark.p_group1
def test_destination_rule_broken(kiali_client, openshift_client, browser):
    destination_rule_broken = get_yaml(istio_objects_path.strpath, DEST_RULE_BROKEN)
    destination_rule_broken_dict = get_dict(istio_objects_path.strpath, DEST_RULE_BROKEN)

    _istio_config_test(kiali_client, openshift_client, browser,
                       destination_rule_broken_dict,
                       destination_rule_broken,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.DESTINATION_RULE.text},
                        {'name': IstioConfigPageFilter.CONFIG.text,
                         'value': IstioConfigValidationType.NOT_VALID.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': destination_rule_broken_dict.metadata.name}
                        ],
                       namespace=BOOKINFO_1,
                       kind='DestinationRule',
                       api_version='networking.istio.io/v1alpha3',
                       service_name=DETAILS,
                       error_messages=['This host has no matching entry in the '
                                       'service registry (service, workload or service entries)'],
                       check_service_details=True)


@pytest.mark.p_crud_resource
@pytest.mark.p_group2
def test_virtual_service(kiali_client, openshift_client, browser):
    virtual_service = get_yaml(istio_objects_path.strpath, VIRTUAL_SERVICE)
    virtual_service_dict = get_dict(istio_objects_path.strpath, VIRTUAL_SERVICE)
    _create_dest_rule_vs(openshift_client, DEST_RULE_VS_REVIEWS)

    _istio_config_test(kiali_client, openshift_client, browser,
                       virtual_service_dict,
                       virtual_service,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.VIRTUAL_SERVICE.text},
                        {'name': IstioConfigPageFilter.CONFIG.text,
                         'value': IstioConfigValidationType.VALID.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': virtual_service_dict.metadata.name}
                        ],
                       namespace=BOOKINFO_1,
                       kind='VirtualService',
                       api_version='networking.istio.io/v1alpha3',
                       service_name=REVIEWS,
                       check_service_details=True)
    _delete_dest_rule_vs(openshift_client, DEST_RULE_VS_REVIEWS)


@pytest.mark.p_crud_resource
@pytest.mark.p_group2
def test_virtual_service_broken(kiali_client, openshift_client, browser):
    virtual_service_broken = get_yaml(istio_objects_path.strpath, VIRTUAL_SERVICE_BROKEN)
    virtual_service_broken_dict = get_dict(istio_objects_path.strpath, VIRTUAL_SERVICE_BROKEN)
    _create_dest_rule_vs(openshift_client, DEST_RULE_VS_REVIEWS)

    _istio_config_test(kiali_client, openshift_client, browser,
                       virtual_service_broken_dict,
                       virtual_service_broken,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.VIRTUAL_SERVICE.text},
                        {'name': IstioConfigPageFilter.CONFIG.text,
                         'value': IstioConfigValidationType.NOT_VALID.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': virtual_service_broken_dict.metadata.name}
                        ],
                       namespace=BOOKINFO_1,
                       kind='VirtualService',
                       api_version='networking.istio.io/v1alpha3',
                       service_name=REVIEWS,
                       error_messages=[
                           "DestinationWeight on route doesn't have a "
                           "valid service (host not found)",
                            'Subset not found'],
                       check_service_details=True)
    _delete_dest_rule_vs(openshift_client, DEST_RULE_VS_REVIEWS)


@pytest.mark.p_crud_resource
@pytest.mark.p_group2
def test_virtual_service_broken_weight(kiali_client, openshift_client, browser):
    virtual_service_broken = get_yaml(istio_objects_path.strpath,
                                      VIRTUAL_SERVICE_BROKEN_WEIGHT)
    virtual_service_broken_dict = get_dict(istio_objects_path.strpath,
                                           VIRTUAL_SERVICE_BROKEN_WEIGHT)
    _create_dest_rule_vs(openshift_client, DEST_RULE_VS_REVIEWS)

    _istio_config_test(kiali_client, openshift_client, browser,
                       virtual_service_broken_dict,
                       virtual_service_broken,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.VIRTUAL_SERVICE.text},
                        {'name': IstioConfigPageFilter.CONFIG.text,
                         'value': IstioConfigValidationType.NOT_VALID.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': virtual_service_broken_dict.metadata.name}
                        ],
                       namespace=BOOKINFO_1,
                       kind='VirtualService',
                       api_version='networking.istio.io/v1alpha3',
                       service_name=REVIEWS,
                       error_messages=['Weight sum should be 100'],
                       check_service_details=False)
    _delete_dest_rule_vs(openshift_client, DEST_RULE_VS_REVIEWS)


@pytest.mark.p_crud_resource
@pytest.mark.p_group3
def test_virtual_service_broken_weight_text(kiali_client, openshift_client, browser):
    virtual_service_broken = get_yaml(istio_objects_path.strpath,
                                      VIRTUAL_SERVICE_BROKEN_WEIGHT_TEXT)
    virtual_service_broken_dict = get_dict(istio_objects_path.strpath,
                                           VIRTUAL_SERVICE_BROKEN_WEIGHT_TEXT)
    _create_dest_rule_vs(openshift_client, DEST_RULE_VS_RATINGS)

    _istio_config_test(kiali_client, openshift_client, browser,
                       virtual_service_broken_dict,
                       virtual_service_broken,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.VIRTUAL_SERVICE.text},
                        {'name': IstioConfigPageFilter.CONFIG.text,
                         'value': IstioConfigValidationType.NOT_VALID.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': virtual_service_broken_dict.metadata.name}
                        ],
                       namespace=BOOKINFO_1,
                       kind='VirtualService',
                       api_version='networking.istio.io/v1alpha3',
                       service_name=RATINGS,
                       error_messages=['Weight must be a number',
                                       'Weight sum should be 100'],
                       check_service_details=False)
    _delete_dest_rule_vs(openshift_client, DEST_RULE_VS_RATINGS)


@pytest.mark.p_crud_resource
@pytest.mark.p_group3
def test_quota_spec(kiali_client, openshift_client, browser):
    quota_spec = get_yaml(istio_objects_path.strpath, QUOTA_SPEC)
    quota_spec_dict = get_dict(istio_objects_path.strpath, QUOTA_SPEC)

    _istio_config_test(kiali_client, openshift_client, browser,
                       quota_spec_dict,
                       quota_spec,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.QUOTA_SPEC.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': 'quota-spec-auto'}
                        ],
                       namespace=BOOKINFO_1,
                       kind='QuotaSpec',
                       api_version='config.istio.io/v1alpha2',
                       service_name=RATINGS,
                       check_service_details=False)


@pytest.mark.p_crud_resource
@pytest.mark.p_group3
def test_quota_spec_binding(kiali_client, openshift_client, browser):
    quota_spec_binding = get_yaml(istio_objects_path.strpath, QUOTA_SPEC_BINDING)
    quota_spec_binding_dict = get_dict(istio_objects_path.strpath, QUOTA_SPEC_BINDING)

    _istio_config_test(kiali_client, openshift_client, browser,
                       quota_spec_binding_dict,
                       quota_spec_binding,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.QUOTA_SPEC_BINDING.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': 'quota-spec-binding-auto'}
                        ],
                       namespace=BOOKINFO_1,
                       kind='QuotaSpecBinding',
                       api_version='config.istio.io/v1alpha2',
                       service_name=RATINGS,
                       check_service_details=False)


@pytest.mark.p_crud_resource
@pytest.mark.p_group3
def test_gateway(kiali_client, openshift_client, browser, pick_namespace):
    gateway = get_yaml(istio_objects_path.strpath, GATEWAY)
    gateway_dict = get_dict(istio_objects_path.strpath, GATEWAY)
    namespace = pick_namespace(BOOKINFO_2)

    _istio_config_test(kiali_client, openshift_client, browser,
                       gateway_dict,
                       gateway,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.GATEWAY.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': gateway_dict.metadata.name}
                        ],
                       namespace=namespace,
                       kind='Gateway',
                       api_version='networking.istio.io/v1alpha3',
                       service_name=REVIEWS,
                       check_service_details=False)


@pytest.mark.p_crud_resource
@pytest.mark.p_group1
def test_service_entry(kiali_client, openshift_client, browser):
    yaml = get_yaml(istio_objects_path.strpath, SERVICE_ENTRY)
    _dict = get_dict(istio_objects_path.strpath, SERVICE_ENTRY)

    _istio_config_test(kiali_client, openshift_client, browser,
                       _dict,
                       yaml,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.SERVICE_ENTRY.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': _dict.metadata.name}
                        ],
                       namespace=BOOKINFO_1,
                       kind='ServiceEntry',
                       api_version='networking.istio.io/v1alpha3',
                       service_name=DETAILS,
                       check_service_details=False)


@pytest.mark.p_crud_resource
@pytest.mark.p_group6
def test_cluster_rbac_config(kiali_client, openshift_client, browser):
    yaml = get_yaml(istio_objects_path.strpath, CLUSTER_RBAC_CONFIG)
    _dict = get_dict(istio_objects_path.strpath, CLUSTER_RBAC_CONFIG)

    _istio_config_test(kiali_client, openshift_client, browser,
                       _dict,
                       yaml,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.CLUSTER_RBAC_CONFIG.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': _dict.metadata.name}
                        ],
                       namespace='istio-system',
                       kind='ClusterRbacConfig',
                       api_version='rbac.istio.io/v1alpha1',
                       service_name=DETAILS,
                       check_service_details=False)


@pytest.mark.p_crud_resource
@pytest.mark.p_group6
def test_rbac_config(kiali_client, openshift_client, browser):
    yaml = get_yaml(istio_objects_path.strpath, RBAC_CONFIG)
    _dict = get_dict(istio_objects_path.strpath, RBAC_CONFIG)

    _istio_config_test(kiali_client, openshift_client, browser,
                       _dict,
                       yaml,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.RBAC_CONFIG.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': _dict.metadata.name}
                        ],
                       namespace=BOOKINFO_1,
                       kind='RbacConfig',
                       api_version='rbac.istio.io/v1alpha1',
                       service_name=DETAILS,
                       check_service_details=False)


@pytest.mark.p_crud_resource
@pytest.mark.p_group8
def test_service_role(kiali_client, openshift_client, browser):
    yaml = get_yaml(istio_objects_path.strpath, SERVICE_ROLE)
    _dict = get_dict(istio_objects_path.strpath, SERVICE_ROLE)

    _istio_config_test(kiali_client, openshift_client, browser,
                       _dict,
                       yaml,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.SERVICE_ROLE.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': _dict.metadata.name}
                        ],
                       namespace='default',
                       kind='ServiceRole',
                       api_version='rbac.istio.io/v1alpha1',
                       service_name=DETAILS,
                       check_service_details=False)


@pytest.mark.p_crud_resource
@pytest.mark.p_group8
def test_service_role_broken(kiali_client, openshift_client, browser):
    yaml = get_yaml(istio_objects_path.strpath, SERVICE_ROLE_BROKEN)
    _dict = get_dict(istio_objects_path.strpath, SERVICE_ROLE_BROKEN)

    _istio_config_test(kiali_client, openshift_client, browser,
                       _dict,
                       yaml,
                       [
                        {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                         'value': IstioConfigObjectType.SERVICE_ROLE.text},
                        {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                         'value': _dict.metadata.name}
                        ],
                       namespace='default',
                       kind='ServiceRole',
                       api_version='rbac.istio.io/v1alpha1',
                       service_name=DETAILS,
                       error_messages=['ServiceRole can only point to current namespace',
                                       'Unable to find all the defined services'],
                       check_service_details=False)


@pytest.mark.p_crud_resource
@pytest.mark.p_group8
def test_service_role_binding(kiali_client, openshift_client, browser):
    _role_yaml = get_yaml(istio_objects_path.strpath, SERVICE_ROLE)
    _role_dict = get_dict(istio_objects_path.strpath, SERVICE_ROLE)
    _istio_config_create(openshift_client, _role_dict, _role_yaml,
                         namespace='default',
                         kind='ServiceRole',
                         api_version='rbac.istio.io/v1alpha1')

    yaml = get_yaml(istio_objects_path.strpath, SERVICE_ROLE_BINDING)
    _dict = get_dict(istio_objects_path.strpath, SERVICE_ROLE_BINDING)
    try:
        _istio_config_test(kiali_client, openshift_client, browser,
                           _dict,
                           yaml,
                           [
                            {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                             'value': IstioConfigObjectType.SERVICE_ROLE_BINDING.text},
                            {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                             'value': _dict.metadata.name}
                            ],
                           namespace='default',
                           kind='ServiceRoleBinding',
                           api_version='rbac.istio.io/v1alpha1',
                           service_name=DETAILS,
                           check_service_details=False)
    finally:
        _istio_config_delete(openshift_client, _role_dict,
                             namespace='default',
                             kind='ServiceRole',
                             api_version='rbac.istio.io/v1alpha1')


@pytest.mark.p_crud_resource
@pytest.mark.p_group8
def test_service_role_binding_broken(kiali_client, openshift_client, browser):
    _role_yaml = get_yaml(istio_objects_path.strpath, SERVICE_ROLE)
    _role_dict = get_dict(istio_objects_path.strpath, SERVICE_ROLE)
    _istio_config_create(openshift_client, _role_dict, _role_yaml,
                         namespace='default',
                         kind='ServiceRole',
                         api_version='rbac.istio.io/v1alpha1')

    yaml = get_yaml(istio_objects_path.strpath, SERVICE_ROLE_BINDING_BROKEN)
    _dict = get_dict(istio_objects_path.strpath, SERVICE_ROLE_BINDING_BROKEN)
    try:
        _istio_config_test(kiali_client, openshift_client, browser,
                           _dict,
                           yaml,
                           [
                            {'name': IstioConfigPageFilter.ISTIO_TYPE.text,
                             'value': IstioConfigObjectType.SERVICE_ROLE_BINDING.text},
                            {'name': IstioConfigPageFilter.ISTIO_NAME.text,
                             'value': _dict.metadata.name}
                            ],
                           namespace='default',
                           kind='ServiceRoleBinding',
                           api_version='rbac.istio.io/v1alpha1',
                           service_name=DETAILS,
                           error_messages=['ServiceRole does not exists in this namespace'],
                           check_service_details=False)
    finally:
        _istio_config_delete(openshift_client, _role_dict,
                             namespace='default',
                             kind='ServiceRole',
                             api_version='rbac.istio.io/v1alpha1')


def _istio_config_create(openshift_client, config_dict, config_yaml, kind, api_version,
                         namespace=BOOKINFO_1):
    openshift_client.delete_istio_config(name=config_dict.metadata.name,
                                         namespace=namespace,
                                         kind=kind,
                                         api_version=api_version)

    openshift_client.create_istio_config(body=config_yaml,
                                         namespace=namespace,
                                         kind=kind,
                                         api_version=api_version)


def _istio_config_delete(openshift_client, config_dict, kind, api_version, namespace=BOOKINFO_1):
    openshift_client.delete_istio_config(name=config_dict.metadata.name,
                                         namespace=namespace,
                                         kind=kind,
                                         api_version=api_version)


def _ui_istio_config_delete(tests, config_dict, namespace=BOOKINFO_1):
    tests.delete_istio_config(name=config_dict.metadata.name,
                              namespace=namespace)


def _create_dest_rule_vs(openshift_client, destination_rule_conf, namespace=BOOKINFO_1):
    destination_rule = get_yaml(istio_objects_path.strpath, destination_rule_conf)
    destination_rule_dict = get_dict(istio_objects_path.strpath, destination_rule_conf)
    _istio_config_create(openshift_client, destination_rule_dict, destination_rule,
                         'DestinationRule',
                         'networking.istio.io/v1alpha3',
                         namespace)


def _delete_dest_rule_vs(openshift_client, destination_rule_conf, namespace=BOOKINFO_1):
    destination_rule_dict = get_dict(istio_objects_path.strpath, destination_rule_conf)
    _istio_config_delete(openshift_client, destination_rule_dict,
                         'DestinationRule',
                         'networking.istio.io/v1alpha3',
                         namespace)


def _istio_config_test(kiali_client, openshift_client, browser, config_dict,
                       config_yaml, filters, namespace, kind, api_version,
                       service_name, check_service_details=False,
                       error_messages=[]):
    tests = IstioConfigPageTest(
        kiali_client=kiali_client, openshift_client=openshift_client, browser=browser)

    if not namespace:
        namespace = BOOKINFO_1

    try:
        _istio_config_create(
            openshift_client, config_dict, config_yaml, kind, api_version, namespace)

        tests.assert_all_items(namespaces=[namespace], filters=filters)

        _istio_config_details_test(kiali_client,
                                   openshift_client,
                                   browser,
                                   config_dict,
                                   config_yaml,
                                   kind,
                                   api_version,
                                   namespace,
                                   error_messages=error_messages)

        if check_service_details:
            _service_details_test(kiali_client,
                                  openshift_client,
                                  browser,
                                  config_dict,
                                  config_yaml,
                                  kind,
                                  api_version,
                                  service_name,
                                  namespace)

        _ui_istio_config_delete(tests, config_dict, namespace)

        tests.assert_all_items(namespaces=[namespace], filters=filters)
    finally:
        _istio_config_delete(openshift_client, config_dict, kind, api_version, namespace)


def _istio_config_details_test(kiali_client, openshift_client, browser, config_dict,
                               config_yaml, kind, api_version, namespace=BOOKINFO_1,
                               error_messages=[]):
    tests = IstioConfigPageTest(
        kiali_client=kiali_client, openshift_client=openshift_client, browser=browser)

    tests.assert_details(name=config_dict.metadata.name,
                         object_type=kind,
                         namespace=namespace,
                         error_messages=error_messages,
                         apply_filters=False)


def _service_details_test(kiali_client, openshift_client, browser, config_dict,
                          config_yaml, kind, api_version, service_name, namespace=BOOKINFO_1):
    tests = ServicesPageTest(
        kiali_client=kiali_client, openshift_client=openshift_client, browser=browser)

    tests.assert_details(name=service_name, namespace=namespace)
