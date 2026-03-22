@echo off
echo ===========================================
echo    Iniciando Podoks ERP + Tienda
echo ===========================================
echo.

echo Levantando contenedores Docker...
docker compose up --build -d

echo.
echo Esperando a que los servicios arranquen (60 segundos)...
timeout /t 100 /nobreak > nul

echo Activando metodo de pago...
docker exec odoo-prestashop-podoks-prestashop-db-1 mysql -u root -proot prestashop -e "UPDATE ps_module SET active = 1 WHERE name = 'ps_wirepayment';"

echo Reiniciando PrestaShop...
docker compose restart prestashop

echo.
echo Esperando a que PrestaShop reinicie (20 segundos)...
timeout /t 20 /nobreak > nul

echo.
echo Ejecutando sincronizacion inicial con Odoo...
python init_sync.py

echo.
echo ===========================================
echo    Todo listo!
echo ===========================================
echo.
echo Odoo ERP:          http://localhost:8069
echo PrestaShop Tienda: http://localhost:8080
echo PrestaShop Admin:  http://localhost:8080/admin
echo   Email:           admin@test.com
echo   Password:        adminpassword
echo.
echo API Key: 9BD4XS8X7IJASRI412JST3EIIBT43RKP
echo ===========================================
pause