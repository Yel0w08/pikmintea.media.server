$COUNT = 10000

for ($i=1; $i -le $COUNT; $i++) {
    git commit --allow-empty -m "commit $i"
}

git push origin main