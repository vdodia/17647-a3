# A3 Full Deployment Guide (Learner Lab Reset Recovery)

All credentials and commands needed to redeploy from scratch after a Learner Lab reset.

---

## Prerequisites

- AWS CLI configured with Learner Lab credentials (copy from Learner Lab → AWS Details)
- `kubectl` installed
- Docker running
- This repo cloned locally

## Credentials Reference

| Item | Value |
|------|-------|
| LabRole ARN | `arn:aws:iam::<ACCOUNT_ID>:role/LabRole` |
| DB Username | `bookadmin` |
| DB Password | `BookstoreA3DbPwd2026` |
| Gemini API Key | `AIzaSyCeRg7BEDuLL11EmsSdGNRdVtEf36COsd4` |
| Gmail (SMTP) | `dodiavirensinh@gmail.com` |
| Gmail App Password | `phgz effg eotc nqql` |
| Andrew ID | `vdodia` |
| CF Stack Name | `bookstore-a3` |
| EKS Cluster Name | `bookstore-dev-BookstoreEKSCluster` |
| Region | `us-east-1` |

---

## Step 1: Update AWS Credentials

Go to Learner Lab → Start Lab → AWS Details → copy credentials into `~/.aws/credentials`.

```bash
# Verify credentials work
aws sts get-caller-identity
```

Note the Account ID — it changes each Lab session. Export it:

```bash
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export LAB_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/LabRole"
echo "Account: $ACCOUNT_ID"
echo "LabRole: $LAB_ROLE_ARN"
```

## Step 2: Deploy CloudFormation Stack (~25-30 min)

```bash
cd ~/Desktop/17647/17647-a3

aws cloudformation create-stack \
  --stack-name bookstore-a3 \
  --template-body file://templates/CF-A3-cmu.yml \
  --parameters \
    ParameterKey=LabRoleARN,ParameterValue="${LAB_ROLE_ARN}" \
    ParameterKey=DBUsername,ParameterValue="bookadmin" \
    ParameterKey=DBPassword,ParameterValue="BookstoreA3DbPwd2026" \
  --region us-east-1
```

Monitor until `CREATE_COMPLETE`:

```bash
watch -n 30 'aws cloudformation describe-stacks --stack-name bookstore-a3 --query "Stacks[0].StackStatus" --output text --region us-east-1'
```

## Step 3: Configure kubectl for EKS

```bash
aws eks update-kubeconfig --name bookstore-dev-BookstoreEKSCluster --region us-east-1
```

Verify nodes are ready:

```bash
kubectl get nodes
```

If you get an access error, you need to add an EKS access entry:

1. Go to AWS Console → EKS → `bookstore-dev-BookstoreEKSCluster` → **Access** tab
2. Click **Create access entry**
3. IAM principal: select your **LabRole** (`arn:aws:iam::<ACCOUNT_ID>:role/LabRole`)
4. Add policy: `AmazonEKSClusterAdminPolicy`, scope: `cluster`
5. Save, then retry `kubectl get nodes`

## Step 4: Create ECR Repositories

```bash
./deploy.sh create-ecr
```

## Step 5: Build and Push Docker Images

```bash
./deploy.sh build
./deploy.sh push
```

## Step 6: Create K8S Namespace and Secrets

```bash
kubectl apply -f k8s/namespace.yaml
```

Create all three secrets (DB, Gemini, Gmail SMTP):

```bash
kubectl create secret generic db-credentials \
  --namespace=bookstore-ns \
  --from-literal=host="$(aws rds describe-db-clusters --region us-east-1 --query 'DBClusters[0].Endpoint' --output text)" \
  --from-literal=username="bookadmin" \
  --from-literal=password="BookstoreA3DbPwd2026" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic app-secrets \
  --namespace=bookstore-ns \
  --from-literal=gemini-api-key="AIzaSyCeRg7BEDuLL11EmsSdGNRdVtEf36COsd4" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic email-credentials \
  --namespace=bookstore-ns \
  --from-literal=smtp-user="dodiavirensinh@gmail.com" \
  --from-literal=smtp-password="phgz effg eotc nqql" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Verify:

```bash
kubectl get secrets -n bookstore-ns
```

## Step 7: Deploy K8S Resources

```bash
./deploy.sh deploy
```

This applies all deployments and services. Wait for pods to be ready:

```bash
kubectl get pods -n bookstore-ns
```

All pods should show `Running` and `1/1` READY.

## Step 8: Create Database Tables

The CF stack creates `books_db` and `customers_db` databases but NOT the tables.
Run this from inside the cluster:

```bash
# Create books table
kubectl exec -n bookstore-ns deploy/book-service -c book-service -- python3 -c "
import mysql.connector, os
conn = mysql.connector.connect(
    host=os.environ['DATABASE_HOST'],
    port=int(os.environ.get('DATABASE_PORT', '3306')),
    user=os.environ['MYSQL_USER'],
    password=os.environ['MYSQL_PASSWORD'],
    database='books_db'
)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS books (
    ISBN        VARCHAR(20)     PRIMARY KEY,
    title       VARCHAR(255)    NOT NULL,
    Author      VARCHAR(255)    NOT NULL,
    description TEXT            NOT NULL,
    genre       VARCHAR(100)    NOT NULL,
    price       DECIMAL(10, 2)  NOT NULL,
    quantity    INT             NOT NULL,
    summary     TEXT
)
''')
conn.commit()
print('books table created')
conn.close()
"

# Create customers table
kubectl exec -n bookstore-ns deploy/customer-service -c customer-service -- python3 -c "
import mysql.connector, os
conn = mysql.connector.connect(
    host=os.environ['DATABASE_HOST'],
    port=int(os.environ.get('DATABASE_PORT', '3306')),
    user=os.environ['MYSQL_USER'],
    password=os.environ['MYSQL_PASSWORD'],
    database='customers_db'
)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS customers (
    id          INT             AUTO_INCREMENT PRIMARY KEY,
    userId      VARCHAR(255)    UNIQUE NOT NULL,
    name        VARCHAR(255)    NOT NULL,
    phone       VARCHAR(50)     NOT NULL,
    address     VARCHAR(255)    NOT NULL,
    address2    VARCHAR(255),
    city        VARCHAR(100)    NOT NULL,
    state       CHAR(2)         NOT NULL,
    zipcode     VARCHAR(10)     NOT NULL
)
''')
conn.commit()
print('customers table created')
conn.close()
"
```

## Step 9: Update url.txt

Get the LoadBalancer hostnames:

```bash
echo "Web BFF:"
kubectl get svc web-bff -n bookstore-ns -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
echo ""
echo "Mobile BFF:"
kubectl get svc mobile-bff -n bookstore-ns -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
echo ""
```

Update `url.txt` with these values:

```
http://<WEB_BFF_HOSTNAME>:80
http://<MOBILE_BFF_HOSTNAME>:80
vdodia
dodiavirensinh@gmail.com
```

Commit:

```bash
git add url.txt && git commit -m "Update url.txt with new LoadBalancer hostnames"
```

## Step 10: Smoke Test

```bash
# Generate a test JWT
JWT=$(python3 -c "
import base64, json, time
header = base64.urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}).encode()).decode().rstrip('=')
payload = base64.urlsafe_b64encode(json.dumps({'sub':'starlord','exp':int(time.time())+3600,'iss':'cmu.edu'}).encode()).decode().rstrip('=')
print(f'{header}.{payload}.fakesignature')
")

WEB_BFF=$(kubectl get svc web-bff -n bookstore-ns -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
MOBILE_BFF=$(kubectl get svc mobile-bff -n bookstore-ns -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test status endpoints
echo "=== Web BFF Status ==="
curl -s -w " HTTP %{http_code}\n" "http://${WEB_BFF}/status"

echo "=== Mobile BFF Status ==="
curl -s -w " HTTP %{http_code}\n" "http://${MOBILE_BFF}/status"

# Test book POST
echo "=== POST /books ==="
curl -s -w "\nHTTP %{http_code}\n" -X POST \
  -H "Authorization: Bearer $JWT" -H "X-Client-Type: Web" -H "Content-Type: application/json" \
  -d '{"ISBN":"978-smoke-test","title":"Smoke Test","Author":"Tester","description":"test","genre":"fiction","price":9.99,"quantity":1}' \
  "http://${WEB_BFF}/books"

# Test book GET
echo "=== GET /books/978-smoke-test ==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "Authorization: Bearer $JWT" -H "X-Client-Type: Web" \
  "http://${WEB_BFF}/books/978-smoke-test"

# Test customer POST
echo "=== POST /customers ==="
curl -s -w "\nHTTP %{http_code}\n" -X POST \
  -H "Authorization: Bearer $JWT" -H "X-Client-Type: Web" -H "Content-Type: application/json" \
  -d '{"userId":"smoketest@gmail.com","name":"Smoke Test","phone":"555-0000","address":"1 Test St","city":"Pittsburgh","state":"PA","zipcode":"15213"}' \
  "http://${WEB_BFF}/customers"

# Test invalid JWT
echo "=== Invalid JWT (should 401) ==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "Authorization: Bearer bad.token.here" -H "X-Client-Type: Web" \
  "http://${WEB_BFF}/books/978-smoke-test"

# Check CRM logs for email
echo "=== CRM Logs ==="
kubectl logs -n bookstore-ns deploy/crm-service --tail=5 -c crm-service
```

Clean up test data:

```bash
kubectl exec -n bookstore-ns deploy/book-service -c book-service -- python3 -c "
import mysql.connector, os
conn = mysql.connector.connect(host=os.environ['DATABASE_HOST'],port=3306,user=os.environ['MYSQL_USER'],password=os.environ['MYSQL_PASSWORD'],database='books_db')
conn.cursor().execute(\"DELETE FROM books WHERE ISBN='978-smoke-test'\"); conn.commit(); conn.close(); print('cleaned')
"
kubectl exec -n bookstore-ns deploy/customer-service -c customer-service -- python3 -c "
import mysql.connector, os
conn = mysql.connector.connect(host=os.environ['DATABASE_HOST'],port=3306,user=os.environ['MYSQL_USER'],password=os.environ['MYSQL_PASSWORD'],database='customers_db')
cur=conn.cursor(); cur.execute(\"DELETE FROM customers WHERE userId='smoketest@gmail.com'\"); cur.execute('ALTER TABLE customers AUTO_INCREMENT = 1'); conn.commit(); conn.close(); print('cleaned')
"
```

## Quick Redeploy (Code Changes Only)

If you only changed code and need to push updates (no infra changes):

```bash
# Rebuild + push one service
docker build -t bookstore/book-service:latest ./book-service/
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "${ECR_BASE}"
docker tag bookstore/book-service:latest "${ECR_BASE}/bookstore/book-service:latest"
docker push "${ECR_BASE}/bookstore/book-service:latest"

# Restart the deployment to pull new image
kubectl rollout restart deployment/book-service -n bookstore-ns
kubectl rollout status deployment/book-service -n bookstore-ns --timeout=120s
```

## Debugging

```bash
kubectl get pods -n bookstore-ns                          # Pod status
kubectl logs deploy/<service> -n bookstore-ns -c <service> --tail=50  # Logs
kubectl describe pod <pod-name> -n bookstore-ns            # Events/errors
kubectl rollout restart deployment/<service> -n bookstore-ns  # Restart
kubectl get svc -n bookstore-ns                            # Service endpoints
kubectl get events -n bookstore-ns --sort-by='.lastTimestamp' | tail -20  # Recent events
```

## Teardown

```bash
kubectl delete namespace bookstore-ns
aws cloudformation delete-stack --stack-name bookstore-a3 --region us-east-1
```
