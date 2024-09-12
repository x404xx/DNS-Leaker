import asyncio
from platform import system as platform_name

import aiohttp
import dns.asyncresolver
from rich.console import Console
from rich.table import Table

LOGO = """
░▒█▀▀▄░▒█▄░▒█░▒█▀▀▀█░▒█░░░░█▀▀░█▀▀▄░█░▄░█▀▀░█▀▀▄░░░
░▒█░▒█░▒█▒█▒█░░▀▀▀▄▄░▒█░░░░█▀▀░█▄▄█░█▀▄░█▀▀░█▄▄▀░▄▄
░▒█▄▄█░▒█░░▀█░▒█▄▄▄█░▒█▄▄█░▀▀▀░▀░░▀░▀░▀░▀▀▀░▀░▀▀░▀▀
                        BY:ˣ⁴⁰⁴ˣˣ"""


class DNSLeakTester:
    def __init__(self):
        self.console = Console()

    async def _ping(self, host):
        param = "-n" if platform_name() == "Windows" else "-c"
        command = ["ping", param, "1", host]
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return await proc.wait() == 0

    async def _get_leak_id(self, session):
        async with session.get("https://bash.ws/id") as response:
            return await response.text()

    async def _fetch_dns_data(self, session, leak_id):
        url = f"https://bash.ws/dnsleak/test/{leak_id}?json"
        async with session.get(url) as response:
            return await response.json()

    async def _get_hostname(self, ip):
        try:
            result = await dns.asyncresolver.resolve_address(ip)
            return result[0].to_text()
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            return "Unknown"

    @staticmethod
    def _create_table(ip_info, dns_servers, hostnames):
        table = Table(title=LOGO, title_style="blue")

        def add_column(name, style, justify="center"):
            table.add_column(name, style=style, justify=justify)

        add_column("Type", "bold deep_sky_blue3")
        add_column("IP", "purple")
        add_column("Hostname", "slate_blue1")
        add_column("Country", "light_green")
        add_column("ASN", "yellow1")

        for server in ip_info:
            table.add_row(
                "IP",
                server["ip"],
                "N/A",
                server.get("country_name", ""),
                server.get("asn", ""),
            )

        for idx, server in enumerate(dns_servers):
            table.add_row(
                "DNS",
                server["ip"],
                hostnames[idx],
                server.get("country_name", ""),
                server.get("asn", ""),
            )

        return table

    def _display_results(self, ip_info, dns_servers, hostnames, conclusions):
        if ip_info or dns_servers:
            table = self._create_table(ip_info, dns_servers, hostnames)
            self.console.print(table)
        else:
            self.console.print("[bold red]No IP Info or DNS Servers Found[/bold red]")

        if conclusions:
            self.console.print("\n[bold cyan]Conclusion:[/bold cyan]")
            for server in conclusions:
                self.console.print(server["ip"])
            self.console.print()

    async def run(self):
        self.console.clear()

        async with aiohttp.ClientSession() as session:
            leak_id = await self._get_leak_id(session)
            ping_tasks = [self._ping(f"{x}.{leak_id}.bash.ws") for x in range(10)]
            await asyncio.gather(*ping_tasks)

            parsed_data = await self._fetch_dns_data(session, leak_id)

        ip_info = [server for server in parsed_data if server["type"] == "ip"]
        dns_servers = [server for server in parsed_data if server["type"] == "dns"]
        conclusions = [
            server
            for server in parsed_data
            if server["type"] == "conclusion" and server.get("ip")
        ]

        hostname_tasks = [self._get_hostname(server["ip"]) for server in dns_servers]
        hostnames = await asyncio.gather(*hostname_tasks)

        self._display_results(ip_info, dns_servers, hostnames, conclusions)
