import json

from itertools import groupby

from kiali.client import KialiClient
from kiali_qe.components.enums import (
    IstioConfigObjectType as OBJECT_TYPE,
    IstioConfigPageFilter as FILTER_TYPE,
    IstioConfigValidation,
    OverviewPageType,
    HealthType as HEALTH_TYPE
)
from kiali_qe.entities.istio_config import IstioConfig, IstioConfigDetails, Rule
from kiali_qe.entities.service import (
    ServiceHealth,
    Service,
    ServiceDetails,
    VirtualService,
    DestinationRule,
    SourceWorkload,
    VirtualServiceWeight
)
from kiali_qe.entities.workload import (
    Workload,
    WorkloadDetails,
    WorkloadPod,
    WorkloadHealth,
    DestinationService
)
from kiali_qe.entities.applications import (
    Application,
    ApplicationDetails,
    AppWorkload,
    ApplicationHealth
)
from kiali_qe.entities.overview import Overview
from kiali_qe.utils import to_linear_string
from kiali_qe.utils.date import parse_from_rest, from_rest_to_ui


class KialiExtendedClient(KialiClient):

    def namespace_list(self):
        """ Returns list of namespaces """
        entities = []
        entities_j = self.get_response('namespaceList')
        if entities_j:
            for entity_j in entities_j:
                entities.append(entity_j['name'])
        return entities

    def service_list(self, namespaces=[], service_names=[]):
        """Returns list of services.
        Args:
            namespaces: can be zero or any number of namespaces
        """
        items = []
        namespace_list = []
        if len(namespaces) > 0:
            namespace_list.extend(namespaces)
        else:
            namespace_list = self.namespace_list()
        # update items
        for _namespace in namespace_list:
            _data = self.get_response('serviceList', namespace=_namespace)
            _services = _data['services']
            # update all the services to our custom entity
            for _service_rest in _services:
                _service = Service(
                    namespace=_namespace,
                    name=_service_rest['name'],
                    istio_sidecar=_service_rest['istioSidecar'],
                    health=self.get_service_health(
                        namespace=_namespace,
                        service_name=_service_rest['name']))
                items.append(_service)
        # filter by service name
        if len(service_names) > 0:
            filtered_list = []
            for _name in service_names:
                filtered_list.extend([_i for _i in items if _name in _i.name])
            return set(filtered_list)
        return items

    def overview_list(self, namespaces=[], overview_type=OverviewPageType.APPS):
        """Returns list of overviews.
        Args:
            namespaces: can be zero or any number of namespaces
        """
        overviews = []
        namespace_list = []
        if len(namespaces) > 0:
            namespace_list.extend(namespaces)
        else:
            namespace_list = self.namespace_list()
        # update items
        for _namespace in namespace_list:
            if overview_type == OverviewPageType.SERVICES:
                _items = self.service_list([_namespace])
            elif overview_type == OverviewPageType.WORKLOADS:
                _items = self.workload_list([_namespace])
            else:
                _items = self.application_list([_namespace])

            _healthy = 0
            _unhealthy = 0
            _degraded = 0
            _na = 0
            for _item in _items:
                if _item.health == HEALTH_TYPE.HEALTHY:
                    _healthy += 1
                if _item.health == HEALTH_TYPE.DEGRADED:
                    _degraded += 1
                if _item.health == HEALTH_TYPE.FAILURE:
                    _unhealthy += 1
                if _item.health == HEALTH_TYPE.NA:
                    _na += 1
            _overview = Overview(
                overview_type=overview_type.text,
                namespace=_namespace,
                items=len(_items),
                healthy=_healthy,
                unhealthy=_unhealthy,
                degraded=_degraded,
                na=_na)
            overviews.append(_overview)
        return overviews

    def application_list(self, namespaces=[], application_names=[]):
        """Returns list of applications.
        Args:
            namespaces: can be zero or any number of namespaces
            application_names: can be zero or any number of applications
        """
        items = []
        namespace_list = []
        if len(namespaces) > 0:
            namespace_list.extend(namespaces)
        else:
            namespace_list = self.namespace_list()
        # update items
        for _namespace in namespace_list:
            _data = self.get_response('appList', namespace=_namespace)
            _applications = _data['applications']
            if _applications:
                for _application_rest in _applications:
                    _application = Application(
                        namespace=_namespace,
                        name=_application_rest['name'],
                        istio_sidecar=_application_rest['istioSidecar'],
                        health=self.get_app_health(
                            namespace=_namespace,
                            app_name=_application_rest['name']))
                    items.append(_application)
        # filter by application name
        if len(application_names) > 0:
            filtered_list = []
            for _name in application_names:
                filtered_list.extend([_i for _i in items if _name in _i.name])
            return set(filtered_list)
        return items

    def workload_list(self, namespaces=[], workload_names=[]):
        """Returns list of workloads.
        Args:
            namespaces: can be zero or any number of namespaces
            workload_names: can be zero or any number of workloads
        """
        items = []
        namespace_list = []
        if len(namespaces) > 0:
            namespace_list.extend(namespaces)
        else:
            namespace_list = self.namespace_list()
        # update items
        for _namespace in namespace_list:
            _data = self.get_response('workloadList', namespace=_namespace)
            _workloads = _data['workloads']
            if _workloads:
                for _workload_rest in _workloads:
                    _labels = self.get_labels(_workload_rest)
                    _workload = Workload(
                        namespace=_namespace,
                        name=_workload_rest['name'],
                        workload_type=_workload_rest['type'],
                        istio_sidecar=_workload_rest['istioSidecar'],
                        app_label='app' in _labels.keys(),
                        version_label='version' in _labels.keys(),
                        health=self.get_workload_health(
                            namespace=_namespace,
                            workload_name=_workload_rest['name']))
                    items.append(_workload)
        # filter by workload name
        if len(workload_names) > 0:
            filtered_list = []
            for _name in workload_names:
                filtered_list.extend([_i for _i in items if _name in _i.name])
            return set(filtered_list)
        return items

    def istio_config_list(self, filters=[]):
        """Returns list of istio config.
        Args:
            namespaces: can be zero or any number of namespaces
        """
        items = []
        namespace_list = []
        # filters
        namespaces = []
        istio_names = []
        istio_types = []
        for _filter in filters:
            if FILTER_TYPE.NAMESPACE.text in _filter['name']:
                namespaces.append(_filter['value'])
            elif FILTER_TYPE.ISTIO_NAME.text in _filter['name']:
                istio_names.append(_filter['value'])
            elif FILTER_TYPE.ISTIO_TYPE.text in _filter['name']:
                istio_types.append(_filter['value'])
        if len(namespaces) > 0:
            namespace_list.extend(namespaces)
        else:
            namespace_list = self.namespace_list()
        # update items
        for _namespace in namespace_list:
            _data = self.get_response('istioConfigList', namespace=_namespace)

            # update DestinationRule
            if len(_data['destinationRules']) > 0 and len(_data['destinationRules']['items']) > 0:
                for _policy in _data['destinationRules']['items']:
                    items.append(IstioConfig(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type=OBJECT_TYPE.DESTINATION_RULE.text,
                        validation=self.get_istio_config_validation(_namespace,
                                                                    'destinationrules',
                                                                    _policy['metadata']['name'])))

            # update Rule
            if len(_data['rules']) > 0:
                for _policy in _data['rules']:
                    items.append(Rule(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type=OBJECT_TYPE.RULE.text))

            # update Rule with Adapter
            if len(_data['adapters']) > 0:
                for _policy in _data['adapters']:
                    items.append(Rule(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type='{}: {}'.format(OBJECT_TYPE.ADAPTER.text, _policy['adapter'])))

            # update Rule with Template
            if len(_data['templates']) > 0:
                for _policy in _data['templates']:
                    items.append(Rule(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type='{}: {}'.format(
                            OBJECT_TYPE.TEMPLATE.text, _policy['template'])))

            # update VirtualService
            if len(_data['virtualServices']) > 0 and len(_data['virtualServices']['items']) > 0:
                for _policy in _data['virtualServices']['items']:
                    items.append(IstioConfig(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type=OBJECT_TYPE.VIRTUAL_SERVICE.text,
                        validation=self.get_istio_config_validation(_namespace,
                                                                    'virtualservices',
                                                                    _policy['metadata']['name'])))

            # update QuotaSpec
            if len(_data['quotaSpecs']) > 0:
                for _policy in _data['quotaSpecs']:
                    items.append(IstioConfig(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type=OBJECT_TYPE.QUOTA_SPEC.text,
                        validation=self.get_istio_config_validation(_namespace,
                                                                    'quotaspecs',
                                                                    _policy['metadata']['name'])))

            # update QuotaSpecBindings
            if len(_data['quotaSpecBindings']) > 0:
                for _policy in _data['quotaSpecBindings']:
                    items.append(IstioConfig(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type=OBJECT_TYPE.QUOTA_SPEC_BINDING.text,
                        validation=self.get_istio_config_validation(_namespace,
                                                                    'quotaspecbindings',
                                                                    _policy['metadata']['name'])))

            # update Gateway
            if len(_data['gateways']) > 0:
                for _policy in _data['gateways']:
                    items.append(IstioConfig(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type=OBJECT_TYPE.GATEWAY.text,
                        validation=self.get_istio_config_validation(_namespace,
                                                                    'gateways',
                                                                    _policy['metadata']['name'])))

            # update serviceEntries
            if len(_data['serviceEntries']) > 0:
                for _policy in _data['serviceEntries']:
                    items.append(IstioConfig(
                        name=_policy['metadata']['name'],
                        namespace=_namespace,
                        object_type=OBJECT_TYPE.SERVICE_ENTRY.text,
                        validation=self.get_istio_config_validation(_namespace,
                                                                    'serviceentries',
                                                                    _policy['metadata']['name'])))

            # not required at this stage. These options not availabe in UI
            # # update all the rules to our custom entity
            # for _rule_rest in _rules:
            #     # update actions
            #     _actions = []
            #     for _action_r in _rule_rest['actions']:
            #         _actions.append(Action.get_from_rest(_action_r))
            #     _match = None
            #     if 'match' in _rule_rest:
            #         _match = _rule_rest['match']
            #     _rule = Rule(
            #         namespace=_namespace,
            #         name=_rule_rest['name'],
            #         actions=_actions,
            #         match=_match)
            #     items.append(_rule)

        # apply filters
        if len(istio_names) > 0 or len(istio_types) > 0:
            name_filtered_list = []
            type_filtered_list = []
            for _name in istio_names:
                name_filtered_list.extend([_i for _i in items if _name in _i.name])
            for _type in istio_types:
                type_filtered_list.extend([_i for _i in items if _type in _i.object_type])
            # If both filters were set, then results must be intersected,
            # as UI applies AND in filters
            if len(istio_names) > 0 and len(istio_types) > 0:
                return set(name_filtered_list).intersection(set(type_filtered_list))
            elif len(istio_names) > 0:
                return set(name_filtered_list)
            elif len(istio_types) > 0:
                return set(type_filtered_list)
        return items

    def istio_config_details(self, namespace, object_type, object_name):
        """Returns details of istio config.
        Args:
            namespaces: namespace where istio config is located
            object_type: type of istio config
            object_name: name of istio config
        """

        _data = self.get_response('istioConfigDetails',
                                  namespace=namespace,
                                  object_type=object_type,
                                  object=object_name)
        config = None
        config_data = None
        if _data:
            # get DestinationRule
            if _data['destinationRule']:
                config_data = _data['destinationRule']

            # get Rule
            if _data['rule']:
                config_data = _data['rule']

            # get VirtualService
            if _data['virtualService']:
                config_data = _data['virtualService']

            # get QuotaSpec
            if _data['quotaSpec']:
                config_data = _data['quotaSpec']

            # get QuotaSpecBindings
            if _data['quotaSpecBinding']:
                config_data = _data['quotaSpecBinding']

            # get Gateway
            if _data['gateway']:
                config_data = _data['gateway']

            # get serviceEntry
            if _data['serviceEntry']:
                config_data = _data['serviceEntry']

            if config_data:
                config = IstioConfigDetails(
                    name=config_data['metadata']['name'],
                    _type=_data['objectType'],
                    text=json.dumps(config_data),
                    validation=self.get_istio_config_validation(namespace,
                                                                object_type,
                                                                object_name),
                    error_messages=self.get_istio_config_messages(namespace,
                                                                  object_type,
                                                                  object_name))
        return config

    def service_details(self, namespace, service_name):
        """Returns details of Service.
        Args:
            namespaces: namespace where Service is located
            service_name: name of Service
        """

        _service_data = self.get_response('serviceDetails',
                                          namespace=namespace,
                                          service=service_name)
        _service = None
        if _service_data:
            _service_rest = self.service_list(namespaces=[namespace],
                                              service_names=[service_name]).pop()
            workloads = []
            if _service_data['workloads']:
                for _wl_data in _service_data['workloads']:
                    # TODO get labels
                    workloads.append(WorkloadDetails(
                        name=_wl_data['name'],
                        workload_type=_wl_data['type'],
                        labels=self.get_labels(_wl_data),
                        created_at=parse_from_rest(_wl_data['createdAt']),
                        resource_version=_wl_data['resourceVersion']))
            source_workloads = []
            if _service_data['dependencies']:
                for _wl_data in _service_data['dependencies']:
                    _wl_names = []
                    for _wl_name in _service_data['dependencies'][_wl_data]:
                        _wl_names.append(_wl_name['name'])
                    source_workloads.append(SourceWorkload(
                        to=_wl_data,
                        workloads=_wl_names))
            virtual_services = []
            if _service_data['virtualServices'] \
                    and len(_service_data['virtualServices']['items']) > 0:
                for _vs_data in _service_data['virtualServices']['items']:
                    _weights = []
                    for _route in _vs_data['spec']['http'][0]['route']:
                        _weights.append(VirtualServiceWeight(
                            host=_route['destination']['host'],
                            subset=_route['destination']['subset']
                            if 'subset' in _route['destination'] else None,
                            port=_route['destination']['port']['number']
                            if 'port' in _route['destination'] else None,
                            status=_route['destination']['status']
                            if 'status' in _route['destination'] else None,
                            weight=_route['weight'] if
                            ('weight' in _route and _route['weight'] != 0) else None)
                        )
                    virtual_services.append(VirtualService(
                        status=self.get_istio_config_validation(
                            _vs_data['metadata']['namespace'],
                            'virtualservices',
                            _vs_data['metadata']['name']),
                        name=_vs_data['metadata']['name'],
                        created_at=parse_from_rest(_vs_data['metadata']['creationTimestamp']),
                        resource_version=_vs_data['metadata']['resourceVersion'],
                        hosts=_vs_data['spec']['hosts'],
                        weights=_weights))
            destination_rules = []
            if _service_data['destinationRules'] \
                    and len(_service_data['destinationRules']['items']) > 0:
                for _dr_data in _service_data['destinationRules']['items']:
                    destination_rules.append(DestinationRule(
                        status=self.get_istio_config_validation(
                            _dr_data['metadata']['namespace'],
                            'destinationrules',
                            _dr_data['metadata']['name']),
                        name=_dr_data['metadata']['name'],
                        host=_dr_data['spec']['host'],
                        traffic_policy=to_linear_string(_dr_data['spec']['trafficPolicy']),
                        subsets=to_linear_string(
                            self.get_subset_labels(_dr_data['spec']['subsets'])),
                        created_at=parse_from_rest(_dr_data['metadata']['creationTimestamp']),
                        resource_version=_dr_data['metadata']['resourceVersion']))
            _ports = ''
            for _port in _service_data['service']['ports']:
                _ports += '{}{} ({}) '.format(_port['protocol'],
                                              ' ' + _port['name'] if _port['name'] != '' else '',
                                              _port['port'])
            _service = ServiceDetails(
                    name=_service_data['service']['name'],
                    istio_sidecar=_service_rest.istio_sidecar,
                    created_at=parse_from_rest(
                        _service_data['service']['createdAt']),
                    resource_version=_service_data['service']['resourceVersion'],
                    service_type=_service_data['service']['type'],
                    ip=_service_data['service']['ip'],
                    ports=_ports.strip(),
                    labels=self.get_labels(_service_data['service']),
                    health=self.get_service_health(
                        namespace=namespace,
                        service_name=service_name),
                    workloads=workloads,
                    source_workloads=source_workloads,
                    virtual_services=virtual_services,
                    destination_rules=destination_rules)
        return _service

    def workload_details(self, namespace, workload_name):
        """Returns details of Workload.
        Args:
            namespaces: namespace where Workload is located
            workload_name: name of Workload
        """

        _workload_data = self.get_response('workloadDetails',
                                           namespace=namespace,
                                           workload=workload_name)
        _workload = None
        if _workload_data:
            _workload_rest = self.workload_list(namespaces=[namespace],
                                                workload_names=[workload_name]).pop()
            _services = []
            if _workload_data['services']:
                for _ws_data in _workload_data['services']:
                    _ports = ''
                    for _port in _ws_data['ports']:
                        _ports += '{}{} ({}) '.format(_port['protocol'],
                                                      ' ' + _port['name']
                                                      if _port['name'] != '' else '',
                                                      _port['port'])
                    _services.append(ServiceDetails(
                        name=_ws_data['name'],
                        created_at=parse_from_rest(_ws_data['createdAt']),
                        service_type=_ws_data['type'],
                        ip=_ws_data['ip'],
                        ports=_ports.strip(),
                        labels=self.get_labels(_ws_data),
                        resource_version=_ws_data['resourceVersion']))
            _destination_services = []
            if _workload_data['destinationServices']:
                for _ds_data in _workload_data['destinationServices']:
                    _destination_services.append(DestinationService(
                        _from=workload_name,
                        name=_ds_data['name'],
                        namespace=_ds_data['namespace']))
            _all_pods = []
            if _workload_data['pods']:
                for _pod_data in _workload_data['pods']:
                    _istio_init_containers = ''
                    _istio_containers = ''
                    if _pod_data['istioContainers']:
                        _istio_containers = _pod_data['istioContainers'][0]['image']
                    if _pod_data['istioInitContainers']:
                        _istio_init_containers = _pod_data['istioInitContainers'][0]['image']
                    _created_by = '{} ({})'.format(_pod_data['createdBy'][0]['name'],
                                                   _pod_data['createdBy'][0]['kind'])
                    _pod = WorkloadPod(
                        name=str(_pod_data['name']),
                        created_at=from_rest_to_ui(_pod_data['createdAt']),
                        created_by=_created_by,
                        labels=self.get_labels(_pod_data),
                        istio_init_containers=str(_istio_init_containers),
                        istio_containers=str(_istio_containers),
                        status=self.get_pod_status(_workload_data['istioSidecar'], _pod_data),
                        phase=_pod_data['status'])
                    _all_pods.append(_pod)

            def get_created_by(nodeid):
                return nodeid.created_by

            _pods = []
            # group by created_by fielts, as it is shown grouped in UI
            for _created_by, _grouped_pods in groupby(_all_pods, key=get_created_by):
                _workload_pods = []
                for _grouped_pod in _grouped_pods:
                    _workload_pods.append(_grouped_pod)
                if len(_workload_pods) > 1:
                    _pod = WorkloadPod(
                        name='{}... ({} replicas)'.format(_pod.name[:-5], len(_workload_pods)),
                        created_at='{} and {}'.format(
                            _pod.created_at, _workload_pods[len(_workload_pods)-1].created_at),
                        created_by=_created_by,
                        labels=_workload_pods[0].labels,
                        istio_init_containers=_workload_pods[0].istio_init_containers,
                        istio_containers=_workload_pods[0].istio_containers,
                        status=_workload_pods[0].status,
                        phase=_workload_pods[0].phase)
                    _pods.append(_pod)
                elif len(_workload_pods) == 1:
                    _pod = WorkloadPod(
                        name='{} (1 replica)'.format(_workload_pods[0].name),
                        created_at=_workload_pods[0].created_at,
                        created_by=_created_by,
                        labels=_workload_pods[0].labels,
                        istio_init_containers=_workload_pods[0].istio_init_containers,
                        istio_containers=_workload_pods[0].istio_containers,
                        status=_workload_pods[0].status,
                        phase=_workload_pods[0].phase)
                    _pods.append(_pod)
            # TODO get labels
            _workload = WorkloadDetails(
                name=_workload_data['name'],
                istio_sidecar=_workload_rest.istio_sidecar,
                workload_type=_workload_data['type'],
                created_at=parse_from_rest(_workload_data['createdAt']),
                resource_version=_workload_data['resourceVersion'],
                health=self.get_workload_health(
                        namespace=namespace,
                        workload_name=_workload_data['name']),
                labels=self.get_labels(_workload_data),
                pods_number=len(_pods),
                services_number=len(_services),
                destination_services_number=len(_destination_services),
                destination_services=_destination_services,
                pods=_pods,
                services=_services)
        return _workload

    def application_details(self, namespace, application_name):
        """Returns details of Application.
        Args:
            namespaces: namespace where Workload is located
            application_name: name of Application
        """

        _application_data = self.get_response('appDetails',
                                              namespace=namespace,
                                              app=application_name)
        _application = None
        if _application_data:
            _application_rest = self.application_list(namespaces=[namespace],
                                                      application_names=[application_name]).pop()
            _workloads = []
            if _application_data['workloads']:
                for _wl_data in _application_data['workloads']:
                    _workloads.append(AppWorkload(
                        name=_wl_data['workloadName'],
                        istio_sidecar=_wl_data['istioSidecar']))
            _services = []
            if 'serviceNames' in _application_data:
                for _service in _application_data['serviceNames']:
                    _services.append(_service)
            _application = ApplicationDetails(
                name=_application_data['name'],
                istio_sidecar=_application_rest.istio_sidecar,
                health=self.get_app_health(
                            namespace=namespace,
                            app_name=_application_data['name']),
                workloads=_workloads,
                services=_services)
        return _application

    def get_service_health(self, namespace, service_name):
        """Returns Health of Service.
        Args:
            namespaces: namespace where Service is located
            service_name: name of Service
        """

        _health_data = self.get_response('serviceHealth',
                                         namespace=namespace,
                                         service=service_name)
        if _health_data:
            return ServiceHealth.get_from_rest(_health_data).is_healthy()
        else:
            return None

    def get_workload_health(self, namespace, workload_name):
        """Returns Health of Workload.
        Args:
            namespaces: namespace where Workload is located
            workload_name: name of Workload
        """

        _health_data = self.get_response('workloadHealth',
                                         namespace=namespace,
                                         workload=workload_name)
        if _health_data:
            return WorkloadHealth.get_from_rest(_health_data).is_healthy()
        else:
            return None

    def get_app_health(self, namespace, app_name):
        """Returns Health of Application.
        Args:
            namespaces: namespace where Application is located
            workload_name: name of Application
        """

        _health_data = self.get_response('appHealth',
                                         namespace=namespace,
                                         app=app_name)
        if _health_data:
            return ApplicationHealth.get_from_rest(_health_data).is_healthy()
        else:
            return None

    def get_istio_config_validation(self, namespace, object_type, object_name):
        """Returns Validation of Istio Config.
        Args:
            namespaces: namespace where Config is located
            object_type: type of the Config
            object: name of Config
        """

        _health_data = self.get_validation('istioConfigDetails',
                                           namespace=namespace,
                                           object_type=object_type,
                                           object=object_name)
        if _health_data:
            if len(_health_data['checks']) > 0:
                if 'error' in set(check['severity'] for check in _health_data['checks']):
                    return IstioConfigValidation.NOT_VALID
                else:
                    return IstioConfigValidation.WARNING
            else:
                return IstioConfigValidation.VALID
        else:
            return IstioConfigValidation.NA

    def get_istio_config_messages(self, namespace, object_type, object_name):
        """Returns Validation Messages of Istio Config.
        Args:
            namespaces: namespace where Config is located
            object_type: type of the Config
            object: name of Config
        """
        _error_messages = []

        _health_data = self.get_validation('istioConfigDetails',
                                           namespace=namespace,
                                           object_type=object_type,
                                           object=object_name)
        if _health_data:
            if len(_health_data['checks']) > 0:
                for _check in _health_data['checks']:
                    _error_messages.append(_check['message'])
        return _error_messages

    def get_labels(self, object_rest):
        _labels = {}
        if 'labels' in object_rest:
            _labels = object_rest['labels']
        return _labels

    def get_subset_labels(self, subsets):
        """
        Returns the labels in subsets as shown in UI: {v1: 'versionv1'}
        """
        _labels = {}
        if subsets:
            for _subset in subsets:
                if 'name' in _subset and 'labels' in _subset:
                    _values = []
                    for _key, _value in _subset['labels'].items():
                        _values.append('{}{}'.format(_key, _value))
                    _labels[_subset['name']] = _values
        return _labels

    def get_response(self, method_name, **kwargs):
        return super(KialiExtendedClient, self).request(method_name=method_name, path=kwargs).json()

    def get_validation(self, method_name, **kwargs):
        return super(KialiExtendedClient, self).request(
            method_name=method_name,
            path=kwargs,
            params={'validate': 'true'}).json()['validation']

    def get_pod_status(self, istioSidecar, pod_data):
        if not istioSidecar or not pod_data['versionLabel'] or not pod_data['appLabel']:
            return IstioConfigValidation.WARNING
        else:
            return IstioConfigValidation.VALID
