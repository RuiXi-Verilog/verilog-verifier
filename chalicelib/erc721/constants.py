from .signature import Signature

ERC721_FX_SIGNATURES = [
    Signature("approve", ["address", "uint256"]),
    Signature("transferFrom", ["address", "address", "uint256"]),
    Signature("setApprovalForAll", ["address", "bool"]),
    Signature("safeTransferFrom", ["address", "address", "uint256"]),
    Signature("safeTransferFrom", ["address", "address", "uint256", "bytes"]),
]

ERC721_ON_RECEIVE_SIGNATURES = [
    Signature("_checkOnERC721Received", ["address", "address", "uint256", "bytes"], ["bool"]),
]

ALLOWANCE_FRONTRUN_FX_SIGNATURES = [
    Signature("setApprovalForAll", ["address", "bool"]),
]

ERC721_EVENT_SIGNATURES = [
    Signature("Transfer", ["address", "address", "uint256"]),
    Signature("Approval", ["address", "address", "uint256"]),
    Signature("ApprovalForAll", ["address", "address", "bool"]),
]

ERC721_GETTERS = [
    Signature("balanceOf", ["address"], ["uint256"]),
    Signature("ownerOf", ["uint256"], ["address"]),
    Signature("getApproved", ["uint256"], ["address"]),
    Signature("isApprovedForAll", ["address", "address"], ["bool"]),
]

ERC721_EVENT_BY_FX = {
    "approve": ERC721_EVENT_SIGNATURES[1], # Approval()
    "transferFrom": ERC721_EVENT_SIGNATURES[0], # Transfer()
    "safeTransferFrom": ERC721_EVENT_SIGNATURES[0], # Transfer()
    "setApprovalForAll": ERC721_EVENT_SIGNATURES[2], # ApprovalForAll()
    #"noEventFunction": {},
}

ALLOWANCE_FRONTRUN_EVENT_BY_FX = {
    "ApprovalForAll": ERC721_EVENT_SIGNATURES[2], 
    "setApprovalForAll": ALLOWANCE_FRONTRUN_FX_SIGNATURES[0],
}
