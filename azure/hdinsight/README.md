# Deployment of Lenses with Docker container 

<a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Flandoop%2Flenses-cloud-templates%2Fmaster%2Fazure%2Fhdinsight%2Fazuredeploy.json" target="_blank">
	<img src="http://azuredeploy.net/deploybutton.png"/>
</a>
<a href="http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Flandoop%2Flenses-cloud-templates%2Fmaster%2Fazure%2Fhdinsight%2Fazuredeploy.json" target="_blank">
    <img src="http://armviz.io/visualizebutton.png"/>
</a>

This template allows you to deploy Lenses as part of an HDInsight cluster with an Apache kafka.

When Lenses started you can use the default credentials `admin/admin`.

## Template Fields

You will need to fill in a few fields to setting up Lenses. The fields are the following:

- Azure Resource Group *(Required)*

- Virtual network *(Required)*

- Subnet of the VNET *(Required)*

- Lenses License. You can get a license [here](https://www.landoop.com/downloads/) *(Required)*

- Port which will be used to run Lenses. *(Required)*

- Kafka Brokers as a comma separated string *(Required)*. For example:
  
``` 
PLAINTEXT://broker.1.url:9092,PLAINTEXT://broker.2.url:9092
```

- Zookeeper as a one-line json payload *(Optional)*. For example: 
  
```
[{url:"zookeeper.1.url:2181", jmx:"zookeeper.1.url:9585"},{url:"zookeeper.2.url:2181", jmx:"zookeeper.2.url:9585"}]
```

- Schema Registry as a one-line json payload *(Optional)*. For example: 
  
```
[{url:"http://schema.registry.1.url:8081",jmx:"schema.registry.1.url:9582"},{url:"http://schema.registry.2.url:8081",jmx:"schema.registry.2.url:9582"}]
```

- Connect as a one-line json payload *(Optional)*. For example:
  
```   
    [{name:"data_science",urls: [{url:"http://connect.worker.1.url:8083",jmx:"connect.worker.1.url:9584"},{url:"http://connect.worker.2.url:8083",jmx:"connect.worker.2.url:9584"}],statuses:"connect-statuses-cluster-a", configs:"connect-configs-cluster-a", offsets:"connect-offsets-cluster-a"}]
```

[ext]: https://github.com/Azure/custom-script-extension-linux
