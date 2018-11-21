# Deployment of Lenses with Docker container 

<a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Flandoop%2Flenses-cloud-templates%2Fmaster%2Fazure%2Fdocker%2Fazuredeploy.json" target="_blank">
	<img src="http://azuredeploy.net/deploybutton.png"/>
</a>
<a href="http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Flandoop%2Flenses-cloud-templates%2Fmaster%2Fazure%2Fdocker%2Fazuredeploy.json" target="_blank">
    <img src="http://armviz.io/visualizebutton.png"/>
</a>

This template allows you to deploy an Ubuntu Server 18.04-LTS VM with Docker (using the [Custom Script Extension][ext]) and starts a Lenses container listening an port 80 based on [HDInsight Apache Kafka](https://docs.microsoft.com/en-us/azure/hdinsight/kafka/apache-kafka-introduction) or your own Apache Kafka infrastructure. This template also creates a persistent data disk which stores the
state of Lenses SQL processors.

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
