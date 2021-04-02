# hdinsight-scripts

Scripts for configuring Lenses - HDInsight

Below you will find two supported auth methods

- Simple: No Auth
- Kerberos: Credentials
- Kerberos: Keytab

## Auth with keytab

If you do not have a keytab, follow the steps below to create one

- Login to a HDInsight node
- Type ktutil

While within ktutil shell, type:

    addent -password -p principal-user -k 1 -e RC4-HMAC

Type the password of the principal-name

Note-0: Do not exit the ktutil shell yet
Note-1: The principal user can be any user that belongs to AD and has been synced in HDInsight ESP Cluster (you can check that from ranger)
Note-2: The principal user needs to have admin privilages in Ranger for the kafka cluster. Lenses expects the user to have admin rights in Kafka

Once you have typed your password, it is time to create the keytab, for that

    wkt /etc/principal-name.keytab

Then exit ktutil by typing `q`

#### Example creating a keytab

    addent -password -p christos-test -k 1 -e RC4-HMAC
    Password for christos-test@LENSES.IO:

    wkt /etc/christos-test.keytab

---

Note: Please ensure that you provided the correct password and principal name otherwise the deployment (see next section) will fail

---

Now make a backup of the keytab and create a base64 string from it

    base64 < principal-name.keytab | tr -d '\n'

Keep somewhere safe both the base64 encoded string and the keytab

#### Example creating a base64 encoded string from the keytab

    base64 < christos.keytab | tr -d '\n'
    B..........2/

Note: Ensure you copy the whole string correctly, otherwise deployment will fail or Lenses will not be able to auth

### Deploy to Azure with Azure HDInsight Templates using a Keytab

Deploy the `esp.json` azure resource template and select the following values

- Cluster Name: The name of the HDInsight cluster
- License Key: Lenses License
- Lenses Admin User Name: self-explanatory
- Lenses Admin Password: self-explanatory
- ESP Enabled: True
- Authenticate with Keytab: True
- Keytab Base64Encoded: The base64 encoded string of the keytab you created. To do that issue:  base64 <principal-name.keytab |tr -d '\n'
- Keytab Principal Name: The principal name of the user from the ktutil stapes
- Install Script URL: The Instal script url. Default: https://raw.githubusercontent.com/lensesio/lenses-cloud-templates/feat/azure_hdinsight_esp/azure/hdinsight/esp/configure.sh

Click deploy and wait for the deployment to finish.

### Already Deployed Lenses Node

If you have a Lenses instance already deployed, then you can SSH into that instance and run the script

#### Clear Lenses Node

Become root

    sudo su -

Create the clean script

```
cat > clean.sh <<EOF
set -x

systemctl stop lenses-io
systemctl stop krb-ticket-init.service
systemctl stop krb-ticket-renewal.service

rm -rf /opt/lenses
rm -rf /etc/krb5.d
rm -f /etc/lenses.env /etc/systemd/system/lenses-io.service 
rm -f /etc/systemd/system/krb-ticket-init.service
rm -f /etc/systemd/system/krb-ticket-renewal.service
rm -f /tmp/lenses-latest-linux64.tar.gz /tmp/lenses-latest-linux64.tar.gz.sha256

systemctl daemon-reload
set +x
EOF
```

Clean

    bash clean.sh


#### Setup

Downloaod the script locally

    cd /opt
    curl -LO https://raw.githubusercontent.com/lensesio/lenses-cloud-templates/feat/azure_hdinsight_esp/azure/hdinsight/esp/configure.sh
    chmod +x configure.sh

Run the script

    bash -x configure.sh \
        -n hdisnightClusterName \
        -V 4.0 \
        -l '{"source":"Lenses.io Ltd","...","details":"Lenses","key":"..."}' \
        -U lenseUsername \
        -P lensesPassword \
        -e True \
        -k True \
        -v 'BQIA....6H2/' \
        -x principalName \
        -L /etc/krb5.d \
        -N krb5.keytab \
        -I 9991 \
        -c False \
        -u  \
        -p  \
        -j False \
        -J  \
        -a False \
        -R 


