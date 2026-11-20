// SPDX-License-Identifier: MIT
// SELF-MADE EXAMPLE ONLY — a deliberately vulnerable vault, written for
// testing the verifier. NOT a real protocol, NOT a live target.
pragma solidity ^0.8.20;

/// @notice Vulnerable on purpose: withdraw() sends ETH *before* zeroing
/// the caller's balance (classic reentrancy). Do not deploy with real funds.
contract Vault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: bal}("");
        require(ok, "send failed");
        balances[msg.sender] = 0;
    }
}
