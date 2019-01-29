import re
from kubernetes import config
from openshift.dynamic import DynamicClient
from openshift.dynamic.exceptions import NotFoundError

from kiali_qe.components.enums import IstioConfigObjectType
from kiali_qe.entities.istio_config import IstioConfig, Rule
from kiali_qe.entities.service import Service
from kiali_qe.entities.workload import Workload
from kiali_qe.entities.applications import Application


class OpenshiftExtendedClient(object):

    def __init__(self):
        self._k8s_client = config.new_client_from_config()
        self._dyn_client = DynamicClient(self._k8s_client)

    @property
    def version(self):
        return self._dyn_client.version

    def _resource(self, kind, api_version='v1'):
        return self._dyn_client.resources.get(kind=kind, api_version=api_version)

    @property
    def _namespace(self):
        return self._resource(kind='Namespace')

    @property
    def _service(self):
        return self._resource(kind='Service')

    @property
    def _cronjob(self):
        return self._resource(kind='CronJob', api_version='v1beta1')

    @property
    def _daemonset(self):
        return self._resource(kind='DaemonSet')

    @property
    def _deployment(self):
        return self._resource(kind='Deployment')

    @property
    def _deploymentconfig(self):
        return self._resource(kind='DeploymentConfig')

    @property
    def _job(self):
        return self._resource(kind='Job', api_version='v1')

    @property
    def _pod(self):
        return self._resource(kind='Pod')

    @property
    def _replicaset(self):
        return self._resource(kind='ReplicaSet')

    @property
    def _replicationcontroller(self):
        return self._resource(kind='ReplicationController')

    @property
    def _statefulset(self):
        return self._resource(kind='StatefulSet')

    def _istio_config(self, kind, api_version):
        return self._resource(kind=kind, api_version=api_version)

    @property
    def _gateway(self):
        return self._istio_config(kind='Gateway', api_version='v1alpha3')

    @property
    def _virtualservice(self):
        return self._istio_config(kind='VirtualService', api_version='v1alpha3')

    @property
    def _destinationrule(self):
        return self._istio_config(kind='DestinationRule', api_version='v1alpha3')

    @property
    def _serviceentry(self):
        return self._istio_config(kind='ServiceEntry', api_version='v1alpha3')

    @property
    def _rule(self):
        return self._istio_config(kind='rule', api_version='v1alpha2')

    @property
    def _logentry(self):
        return self._istio_config(kind='logentry', api_version='v1alpha2')

    @property
    def _kubernetes(self):
        return self._istio_config(kind='kubernetes', api_version='v1alpha2')

    @property
    def _metric(self):
        return self._istio_config(kind='metric', api_version='v1alpha2')

    @property
    def _kubernetesenv(self):
        return self._istio_config(kind='kubernetesenv', api_version='v1alpha2')

    @property
    def _prometheus(self):
        return self._istio_config(kind='prometheus', api_version='v1alpha2')

    @property
    def _stdio(self):
        return self._istio_config(kind='stdio', api_version='v1alpha2')

    @property
    def _quotaspec(self):
        return self._istio_config(kind='QuotaSpec', api_version='v1alpha2')

    @property
    def _quotaspecbinding(self):
        return self._istio_config(kind='QuotaSpecBinding', api_version='v1alpha2')

    def namespace_list(self):
        """ Returns list of namespaces """
        _response = self._namespace.get()
        namespaces = []
        for _item in _response.items:
            namespaces.append(_item.metadata.name)
        return namespaces

    def namespace_exists(self, namespace):
        """ Returns True if given namespace exists. False otherwise. """
        try:
            self._namespace.get(name=namespace)
            return True
        except NotFoundError:
            return False

    def application_list(self, namespaces=[], application_names=[]):
        """ Returns list of applications """
        result = {}
        workloads = []
        workloads.extend(self.workload_list(namespaces=namespaces))

        regex = re.compile('(-v\\d+-.*)?(-v\\d+$)?(-(\\w{0,7}\\d+\\w{0,7})$)?')
        for workload in workloads:
            # TODO: istio side car and health needs to be added
            name = workload.app_label if workload.app_label else re.sub(regex, '', workload.name)
            result[name+workload.namespace] = Application(name, workload.namespace)
        # filter by service name
        if len(application_names) > 0:
            filtered_list = []
            for _name in application_names:
                filtered_list.extend([_i for _i in result.values() if _name in _i.name])
            return set(filtered_list)
        return result.values()

    def service_list(self, namespaces=[], service_names=[]):
        """ Returns list of services
        Args:
            namespace: Namespace of the service, optional
        """
        items = []
        _raw_items = []
        if len(namespaces) > 0:
            # update items
            for _namespace in namespaces:
                _response = self._service.get(namespace=_namespace)
                _raw_items.extend(_response.items)
        else:
            _response = self._service.get()
            _raw_items.extend(_response.items)
        for _item in _raw_items:
            # update all the services to our custom entity
            # TODO: istio side car and heath needs to be added
            _service = Service(
                namespace=_item.metadata.namespace,
                name=_item.metadata.name,
                istio_sidecar=None,
                health=None)
            items.append(_service)
        # filter by service name
        if len(service_names) > 0:
            filtered_list = []
            for _name in service_names:
                filtered_list.extend([_i for _i in items if _name in _i.name])
            return set(filtered_list)
        return items

    def workload_list(self, namespaces=[], workload_names=[]):
        """ Returns list of workloads """
        result = []
        result.extend(self._workload_list('_cronjob', 'CronJob',
                                          namespaces=namespaces, workload_names=workload_names))
        result.extend(self._workload_list('_daemonset', 'DaemonSet',
                                          namespaces=namespaces, workload_names=workload_names))
        result.extend(self._workload_list('_deployment', 'Deployment',
                                          namespaces=namespaces, workload_names=workload_names))
        result.extend(self._workload_list('_deploymentconfig', 'DeploymentConfig',
                                          namespaces=namespaces, workload_names=workload_names))
        # TODO apply Job filters
        result.extend(self._workload_list('_job', 'Job', namespaces=namespaces,
                                          workload_names=workload_names))
        # TODO apply Pod filters
        result.extend(self._workload_list('_pod', 'Pod', namespaces=namespaces,
                                          workload_names=workload_names))
        result.extend(self._workload_list('_replicaset', 'ReplicaSet',
                                          namespaces=namespaces, workload_names=workload_names))
        result.extend(self._workload_list('_replicationcontroller', 'ReplicationController',
                                          namespaces=namespaces, workload_names=workload_names))
        result.extend(self._workload_list('_statefulset', 'StatefulSet',
                                          namespaces=namespaces, workload_names=workload_names))
        return result

    def _workload_list(self, attribute_name, workload_type,
                       namespaces=[], workload_names=[]):
        """ Returns list of workload
        Args:
            attribute_name: the attribute of class for getting workload
            workload_type: the type of workload
            namespace: Namespace of the workload, optional
            workload_names: Names of the workloads, optional
        """
        items = []
        _raw_items = []
        if len(namespaces) > 0:
            # update items
            for _namespace in namespaces:
                _response = getattr(self, attribute_name).get(namespace=_namespace)
                if hasattr(_response, 'items'):
                    _raw_items.extend(_response.items)
        else:
            _response = getattr(self, attribute_name).get()
            if hasattr(_response, 'items'):
                _raw_items.extend(_response.items)
        for _item in _raw_items:
            # update all the workloads to our custom entity
            # TODO: istio side car and labels needs to be added
            _workload = Workload(
                name=_item.metadata.name,
                namespace=_item.metadata.namespace,
                workload_type=workload_type,
                istio_sidecar=self._contains_sidecar(_item),
                app_label=self._get_label(_item, 'app'),
                version_label=self._get_label(_item, 'version'))
            items.append(_workload)
        # filter by workload name
        if len(workload_names) > 0:
            filtered_list = []
            for _name in workload_names:
                filtered_list.extend([_i for _i in items if _name in _i.name])
            return set(filtered_list)
        return items

    def _contains_sidecar(self, item):
        try:
            return item.spec.template.metadata.annotations['sidecar.istio.io/status'] is not None
        except (KeyError, AttributeError, TypeError):
            return False

    def _get_label(self, item, label):
        try:
            return item.metadata.labels[label]
        except (KeyError, AttributeError, TypeError):
            return None

    def istio_config_list(self, namespaces=[], config_names=[]):
        """ Returns list of Istio Configs """
        result = []
        result.extend(self._resource_list('_gateway', 'Gateway',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_virtualservice', 'VirtualService',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_destinationrule', 'DestinationRule',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_serviceentry', 'ServiceEntry',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_rule', 'Rule',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_kubernetesenv', 'Adapter',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_prometheus', 'Adapter',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_stdio', 'Adapter',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_logentry', 'Template',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_kubernetes', 'Template',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_metric', 'Template',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_quotaspec', 'QuotaSpec',
                                          namespaces=namespaces, resource_names=config_names))
        result.extend(self._resource_list('_quotaspecbinding', 'QuotaSpecBinding',
                                          namespaces=namespaces, resource_names=config_names))

        return result

    def _resource_list(self, attribute_name, resource_type,
                       namespaces=[], resource_names=[]):
        """ Returns list of Resource
        Args:
            attribute_name: the attribute of class for getting resource
            resource_type: the type of resource
            namespace: Namespace of the resource, optional
            resource_names: Names of the r, optional
        """
        items = []
        _raw_items = []
        if len(namespaces) > 0:
            # update items
            for _namespace in namespaces:
                _response = getattr(self, attribute_name).get(namespace=_namespace)
                if hasattr(_response, 'items'):
                    _raw_items.extend(_response.items)
        else:
            _response = getattr(self, attribute_name).get()
            if hasattr(_response, 'items'):
                _raw_items.extend(_response.items)
        for _item in _raw_items:
            if str(resource_type) == IstioConfigObjectType.RULE.text:
                _rule = Rule(name=_item.metadata.name,
                             namespace=_item.metadata.namespace,
                             object_type=resource_type)
                # append this item to the final list
                items.append(_rule)
            elif str(resource_type) == IstioConfigObjectType.ADAPTER.text or\
                    str(resource_type) == IstioConfigObjectType.TEMPLATE.text:
                _rule = Rule(name=_item.metadata.name,
                             namespace=_item.metadata.namespace,
                             object_type='{}: {}'.format(
                                 resource_type, _item.kind))
                # append this item to the final list
                items.append(_rule)
            else:
                _config = IstioConfig(name=_item.metadata.name,
                                      namespace=_item.metadata.namespace,
                                      object_type=resource_type)
                # append this item to the final list
                items.append(_config)
        # filter by resource name
        if len(resource_names) > 0:
            filtered_list = []
            for _name in resource_names:
                filtered_list.extend([_i for _i in items if _name in _i.name])
            return set(filtered_list)
        return items

    def delete_istio_config(self, name, namespace, kind, api_version):
        try:
            self._istio_config(kind=kind, api_version=api_version).delete(name=name,
                                                                          namespace=namespace)
        except NotFoundError:
            pass

    def create_istio_config(self, body, namespace, kind, api_version):
        resp = self._istio_config(kind=kind, api_version=api_version).create(body=body,
                                                                             namespace=namespace)
        return resp
