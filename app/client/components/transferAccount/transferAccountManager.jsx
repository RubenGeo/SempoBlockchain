import React, {lazy, Suspense} from 'react';
import styled from 'styled-components';
import { connect } from 'react-redux';

import { StyledButton, ModuleBox, ModuleHeader } from '../styledElements'
import AsyncButton from '../AsyncButton.jsx'
const SingleDatePickerWrapper = lazy(() => import('./SingleDatePickerWrapper.jsx'));
// import SingleDatePickerWrapper from './SingleDatePickerWrapper.jsx'
import NewTransferManager from '../management/newTransferManager.jsx'
import DateTime from '../dateTime.jsx';

import { editTransferAccount } from '../../reducers/transferAccountReducer'
import { createTransferRequest } from '../../reducers/creditTransferReducer'
import { formatMoney } from "../../utils";

const mapStateToProps = (state, ownProps) => {
  return {
    login: state.login,
    creditTransfers: state.creditTransfers,
    transferAccounts: state.transferAccounts,
    transferAccount: state.transferAccounts.byId[parseInt(ownProps.transfer_account_id)]
  };
};

const mapDispatchToProps = (dispatch) => {
  return {
    createTransferRequest: (payload) => dispatch(createTransferRequest(payload)),
    editTransferAccountRequest: (body, path) => dispatch(editTransferAccount({body, path})),
  };
};

class TransferAccountManager extends React.Component {
  constructor() {
    super();
    this.state = {
        action: 'select',
        transfer_type: 'ALL',
        create_transfer_type: 'WITHDRAWAL',
        newTransfer: false,
        transfer_amount: '',
        showSpreadsheetData: true,
        balance: '',
        location: '',
        is_approved: 'n/a',
        one_time_code: '',
        focused: false,
        payable_epoch: null,
        payable_period_type: 'n/a',
        payable_period_length: 1,
        is_vendor: null,
    };
    this.handleChange = this.handleChange.bind(this);
    this.handleClick = this.handleClick.bind(this);
    this.createNewTransfer = this.createNewTransfer.bind(this);
    this.onSave = this.onSave.bind(this);
    this.onNewTransfer = this.onNewTransfer.bind(this);
  }

  componentDidMount() {
      this.updateTransferAccountState()
  }

  componentDidUpdate(newProps){
     if (this.props.creditTransfers !== newProps.creditTransfers && !this.props.creditTransfers.createStatus.isRequesting) {
         this.setState({newTransfer: false});
         this.updateTransferAccountState()
     }
  }

  updateTransferAccountState() {
      const transferAccountID = parseInt(this.props.transfer_account_id);
      const transferAccount = this.props.transferAccounts.byId[transferAccountID];

      if (transferAccount !== null) {
          this.setState({
              balance: transferAccount.balance,
              created: transferAccount.created,
              location: transferAccount.location,
              is_approved: transferAccount.is_approved,
              payable_epoch: transferAccount.payable_epoch,
              payable_period_type: transferAccount.payable_period_type,
              payable_period_length: transferAccount.payable_period_length,
              is_vendor: transferAccount.is_vendor,
          });
      }
  }

  editTransferAccount() {
    const balance = this.state.balance * 100;
    const approve = (this.state.is_approved == 'n/a' ? null : this.state.is_approved);
    const nfc_card_id = this.state.nfc_card_id;
    const qr_code = this.state.qr_code;
    const phone = this.state.phone;
    const location = this.state.location;

    if (this.state.payable_epoch) {
        var payable_epoch = this.state.payable_epoch._d;
    }

    const payable_period_length = this.state.payable_period_length;
    const payable_period_type = (this.state.payable_period_type === 'n/a' ? null : this.state.payable_period_type);

    const single_transfer_account_id = this.props.transfer_account_id.toString();

    this.props.editTransferAccountRequest(
        {
            balance,
            approve,
            phone,
            nfc_card_id,
            qr_code,
            location,
            payable_epoch,
            payable_period_length,
            payable_period_type,
        },
        single_transfer_account_id
    );
  }

  handleChange (evt) {
    this.setState({ [evt.target.name]: evt.target.value });
  }


  handleClick() {
    this.setState(prevState => ({
      newTransfer: !prevState.newTransfer
    }));
  }

  onSave() {
      this.editTransferAccount();
  }

  onNewTransfer() {
      this.handleClick();
  }

  createNewTransfer() {
      if (this.state.transfer_amount > 0) {
          var transfer_account_ids = this.props.transfer_account_id;
          var transfer_amount = this.state.transfer_amount * 100;
          var transfer_type = this.state.create_transfer_type;
          var credit_transfer_type_filter = this.state.transfer_type;
          const transfer_account_filter = this.props.vendors ? '?account_type=vendor' : '?account_type=beneficiary';
          const credit_transfer_filter = `?transfer_account_ids=${transfer_account_ids}&transfer_type=${credit_transfer_type_filter}`;
          var id = null;

          this.props.createTransferRequest({transfer_account_ids, transfer_amount, transfer_type, credit_transfer_filter, transfer_account_filter, id})
      }
  }

  render() {

      if (this.state.newTransfer) {
          var newTransfer = <NewTransferManager transfer_account_ids={[this.props.transfer_account_id]} cancelNewTransfer={() => this.onNewTransfer()} />
      } else {
          newTransfer = null;
      }

      const displayAmount = <p style={{margin: 0, fontWeight: 100, fontSize: '16px'}}>{formatMoney(this.state.balance / 100)}</p>;

      if (!window.IS_USING_BITCOIN) {
        var tracker_link = (
          'https://' + window.ETH_CHAIN_NAME  +  (window.ETH_CHAIN_NAME? '.':'')
          + 'etherscan.io/address/' + this.props.transferAccount.blockchain_address.address
        )
      } else {
        tracker_link = (
          'https://www.blockchain.com/' + (window.IS_BITCOIN_TESTNET? 'btctest' : 'btc') +
          '/address/' + this.props.transferAccount.blockchain_address.address
        )
      }

      var summaryBox =
          <ModuleBox>
              <SummaryBox>
                  <TopContent>
                      <UserSVG src={(this.state.is_vendor === true ? "/static/media/store.svg" : "/static/media/user.svg")}/>
                      <p style={{margin: '0 1em', fontWeight: '500'}}>{(this.state.is_vendor === true ? 'Vendor' : window.BENEFICIARY_TERM)}</p>
                  </TopContent>
                  <BottomContent>
                      <FontStyling>Balance: <span style={{margin: 0, fontWeight: 100, fontSize: '16px'}}>{displayAmount}</span></FontStyling>
                      <FontStyling>Created: <span style={{margin: 0, fontWeight: 100, fontSize: '16px'}}><DateTime created={this.state.created}/></span></FontStyling>
                      <FontStyling>Address:
                        <span style={{margin: 0, fontWeight: 100, fontSize: '16px'}}>
                          <p style={{margin: 0, fontWeight: 100, fontSize: '16px'}}>
                            <a  href={tracker_link}
                                     target="_blank">
                            {this.props.transferAccount.blockchain_address.address.substring(window.IS_USING_BITCOIN? 0:2,7) + '...'}
                            </a>
                          </p>
                        </span>
                      </FontStyling>

                  </BottomContent>
              </SummaryBox>
          </ModuleBox>;

      return (
          <div style={{display: 'flex', flexDirection: 'column'}}>

              {summaryBox}

              {newTransfer}

              {this.props.login.adminTier !== 'view' ?
              <ModuleBox>
                  <Wrapper>
                      <TopRow>
                          <ModuleHeader>DETAILS</ModuleHeader>
                          <ButtonWrapper>
                            <StyledButton onClick={this.onNewTransfer} style={{fontWeight: '400', margin: '0em 1em', lineHeight: '25px', height: '25px'}}>NEW TRANSFER</StyledButton>
                            <AsyncButton onClick={this.onSave} miniSpinnerStyle={{height: '10px', width: '10px'}} buttonStyle={{display: 'inline-flex', fontWeight: '400', margin: '0em', lineHeight: '25px', height: '25px'}} isLoading={this.props.transferAccounts.editStatus.isRequesting} buttonText="SAVE"/>
                          </ButtonWrapper>
                      </TopRow>
                      <Row style={{margin: '0em 1em'}}>
                          <SubRow>
                              <InputLabel>Location: </InputLabel><ManagerInput name="location" placeholder="n/a" value={this.state.location || ''} onChange={this.handleChange}/>
                          </SubRow>
                          <SubRow>
                              <InputLabel>Status: </InputLabel>
                              <StatusSelect name="is_approved" value={this.state.is_approved} onChange={this.handleChange}>
                                  <option name="is_approved" disabled value="n/a">n/a</option>
                                  <option name="is_approved" value="true">Approved</option>
                                  <option name="is_approved" value="false">Unapproved</option>
                              </StatusSelect>
                          </SubRow>
                          <SubRow>
                              <InputLabel>{(this.state.one_time_code !== '') ? 'One Time Code:' : '' }</InputLabel><ManagerText>{this.state.one_time_code}</ManagerText>
                          </SubRow>
                      </Row>
                      <Row style={{margin: '0em 1em'}}>
                          <SubRow style={{width: '50%'}}>
                              <InputLabel>Payment Cycle Start Date: </InputLabel>
                            <Suspense fallback={<div>Loading...</div>}>
                              <SingleDatePickerWrapper
                                  numberOfMonths={1}
                                  date={this.state.date} // momentPropTypes.momentObj or null
                                  onDateChange={date => this.setState({ payable_epoch: date })}
                                  focused={this.state.focused} // PropTypes.bool
                                  onFocusChange={() => this.setState({ focused: !this.state.focused })} // PropTypes.func.isRequired
                                  id="your_unique_id" // PropTypes.string.isRequired,
                                  withPortal
                                  hideKeyboardShortcutsPanel
                                  // showDefaultInputIcon
                                  // inputIconPosition="after"
                                  isOutsideRange
                              />
                            </Suspense>
                          </SubRow>
                          <SubRow>
                              <InputLabel>Payment Cycle: </InputLabel>
                              <StatusSelect name="payable_period_type" value={this.state.payable_period_type === null ? 'n/a' : this.state.payable_period_type} onChange={this.handleChange}>
                                  <option name="payable_period_type" disabled value="n/a">n/a</option>
                                  <option name="payable_period_type" value="day">Daily</option>
                                  <option name="payable_period_type" value="week">Weekly</option>
                                  <option name="payable_period_type" value="month">Monthly</option>
                              </StatusSelect>
                          </SubRow>
                      </Row>
                  </Wrapper>
              </ModuleBox> : <ModuleBox><p>You don't have access to user details</p></ModuleBox> }

          </div>
      );
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(TransferAccountManager);

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
`;

const TopRow = styled.div`
  display: flex;
  width: 100%;
  justify-content: space-between;
`;

const ButtonWrapper = styled.div`
  margin: auto 1em;
  @media (max-width: 767px) {
  margin: auto 1em;
  display: flex;
  flex-direction: column;
  }
`;

const Row = styled.div`
  display: flex;
  align-items: center;
  @media (max-width: 767px) {
  width: calc(100% - 2em);
  margin: 0 1em;
  flex-direction: column;
  align-items: end;
  }
`;

const SubRow = styled.div`
  display: flex;
  align-items: center;
  width: 33%;
  @media (max-width: 767px) {
  width: 100%;
  justify-content: space-between;
  }
`;

const ManagerInput = styled.input`
  color: #555;
  border: solid #d8dbdd;
  border-width: 0 0 1px 0;
  outline: none;
  margin-left: 0.5em;
  width: 50%;
  font-size: 15px;
  &:focus {
  border-color: #2D9EA0;
  }
`;

const InputLabel = styled.p`
  font-size: 15px;
`;

const StatusSelect = styled.select`
  border: none;
  background-color: #FFF;
  margin-left: 0.5em;
  font-size: 15px;
  @media (max-width: 767px) {
  width: 50%;
  }
`;

const ManagerText = styled.p`
  color: #555;
  margin-left: 0.5em;
  width: 50%;
  font-size: 15px;
`;

const UserSVG = styled.img`
  width: 40px;
  height: 40px;
`;

const SummaryBox = styled.div`
  display: flex;
  padding: 1em;
  align-items: center;
  justify-content: space-between;
  @media (max-width: 767px) {
  flex-direction: column;
  }
`;

const TopContent = styled.div`
  width: 100%;
  align-items: center;
  display: flex;
  @media (max-width: 767px) {
  padding: 0 0 1em;
  }
`;

const BottomContent = styled.div`
  max-width: 350px;
  width: 100%;
  align-items: center;
  display: flex;
  justify-content: space-between;
`;

const FontStyling = styled.span`
    font-weight: 500;
    font-size: 12px;
`;
