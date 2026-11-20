// SPDX-License-Identifier: MIT
// SELF-MADE EXAMPLE ONLY — the same vault interface, fixed.
// Checks-effects-interactions + a reentrancy guard. The same PoC that
// drains VulnerableVault must FAIL against this contract.
pragma solidity ^0.8.20;

contract Vault {
    mapping(address => uint256) public balances;
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "reentrant call");
        locked = true;
        _;
        locked = false;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external nonReentrant {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "no balance");
        balances[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: bal}("");
        require(ok, "send failed");
    }
}
