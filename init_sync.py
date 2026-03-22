import subprocess

cmd = [
    "docker", "exec", "-i",
    "odoo-prestashop-podoks-odoo-1",
    "odoo", "shell", "-d", "odoo", "--no-http"
]

script = """
env['prestashop.sync'].sync_products()
env['prestashop.sync'].push_stock_to_prestashop()
env['prestashop.sync'].sync_orders()
env.cr.commit()
print("Sincronizacion completada")
"""

process = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
stdout, stderr = process.communicate(input=script.encode())
print(stdout.decode())