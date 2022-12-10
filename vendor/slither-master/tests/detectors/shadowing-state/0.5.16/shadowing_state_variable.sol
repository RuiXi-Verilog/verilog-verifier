contract BaseContract{
    address owner;

    modifier isOwner(){
        require(owner == msg.sender);
        _;
    }

}

contract DerivedContract is BaseContract{
    address owner;

    constructor() public {
        owner = msg.sender;
    }

    function withdraw() isOwner() external{
        msg.sender.transfer(address(this).balance);
    }
}
