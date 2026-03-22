@echo off
echo ===========================================
echo    Iniciando Podoks ERP + Tienda
echo ===========================================
echo.

echo Levantando contenedores Docker...
docker compose up --build -d

echo.
echo Esperando a que los servicios arranquen (60 segundos)...
timeout /t 60 /nobreak > nul

echo.
echo Configurando PrestaShop...
docker exec odoo-prestashop-podoks-prestashop-db-1 mysql -u root -proot prestashop -e "UPDATE ps_webservice_account SET key_value = '9BD4XS8X7IJASRI412JST3EIIBT43RKP' WHERE id_webservice_account = 1; UPDATE ps_configuration SET value = '1' WHERE name = 'PS_WEBSERVICE'; UPDATE ps_configuration SET value = 'localhost:8080' WHERE name IN ('PS_SHOP_DOMAIN', 'PS_SHOP_DOMAIN_SSL');"

echo Configurando permisos de la API key...
docker exec odoo-prestashop-podoks-prestashop-db-1 mysql -u root -proot prestashop -e "SET @id = (SELECT id_webservice_account FROM ps_webservice_account WHERE key_value = '9BD4XS8X7IJASRI412JST3EIIBT43RKP'); DELETE FROM ps_webservice_account_permissions WHERE id_webservice_account = @id; INSERT INTO ps_webservice_account_permissions (id_webservice_account, resource, method) VALUES (@id, 'products', 'GET'), (@id, 'products', 'POST'), (@id, 'products', 'PUT'), (@id, 'products', 'DELETE'), (@id, 'orders', 'GET'), (@id, 'orders', 'PUT'), (@id, 'customers', 'GET'), (@id, 'stock_availables', 'GET'), (@id, 'stock_availables', 'PUT');"

echo Activando metodo de pago...
docker exec odoo-prestashop-podoks-prestashop-db-1 mysql -u root -proot prestashop -e "UPDATE ps_module SET active = 1 WHERE name = 'ps_wirepayment';"

echo Fijando carpeta admin...
docker exec odoo-prestashop-podoks-prestashop-db-1 mysql -u root -proot prestashop -e "UPDATE ps_configuration SET value = 'admin' WHERE name = 'PS_ADMIN_FOLDER';"

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