import React from 'react';
import { connect } from 'react-redux';
import styled, {ThemeProvider} from 'styled-components';

import { browserHistory } from "../../app.jsx";
import { PageWrapper, WrapperDiv, ModuleBox, StyledButton } from '../styledElements.js'
import { LightTheme } from '../theme.js'

import TransferAccountListWithFilterWrapper from '../transferAccount/transferAccountListWithFilterWrapper.jsx';
import UploadButton from "../uploader/uploadButton.jsx";

import { loadTransferAccounts } from "../../reducers/transferAccountReducer";

const mapStateToProps = (state) => {
  return {
    transferAccounts: state.transferAccounts,
    mergedTransferAccountUserList: Object.keys(state.transferAccounts.byId).map((id) => {return {...{id, ...state.users.byId[state.transferAccounts.byId[id].primary_user_id]}, ...state.transferAccounts.byId[id]}}),
    users: state.users,
  };
};

const mapDispatchToProps = (dispatch) => {
  return {
    loadTransferAccountList: (query, path) => dispatch(loadTransferAccounts({query, path})),
  };
};


class TransferAccountListPage extends React.Component {
  componentDidMount() {
      this.buildFilterForAPI()
  }
  
  componentDidUpdate(newProps) {
      if (newProps.location.pathname !== location.pathname) {
          this.buildFilterForAPI()
      }
  }

  buildFilterForAPI() {
      if (location.pathname.includes('vendors')) {
          console.log('vendor filter:', location.search);
          var query = {account_type: 'vendor'};

      } else if (location.pathname.includes(window.BENEFICIARY_TERM_PLURAL.toLowerCase())) {
          console.log('beneficiary filter:', location.search);
          query = {account_type: 'beneficiary'};

      } else {
          console.log('no filter');
          query = null;
      }

      const path = null;

      this.props.loadTransferAccountList(query, path);
  }
  
  render() {
    let beneficiaryTerm = window.BENEFICIARY_TERM;
    
    const is_vendor = location.pathname.includes('vendors');
    const is_beneficiary = location.pathname.includes(window.BENEFICIARY_TERM_PLURAL.toLowerCase());

    if (is_vendor || is_beneficiary) {
        // just vendors or beneficiaries
        var transferAccountList = this.props.mergedTransferAccountUserList.filter(transferAccount => {return transferAccount.is_vendor === is_vendor})
    } else {
        // all transfer accounts
        transferAccountList = this.props.mergedTransferAccountUserList
    }
    
    let isNoData = (Object.keys(transferAccountList).length === 0);

    let uploadButtonText =
      <NoDataMessageWrapper>
        <IconSVG src="/static/media/no_data_icon.svg"/>
        <p>There is no data available. Please upload a spreadsheet.</p>
      </NoDataMessageWrapper>;
    
    if (isNoData && this.props.transferAccounts.loadStatus.isRequesting !== true) {
      return(
        <PageWrapper>
            <ModuleBox>
                <NoDataMessageWrapper>
                  <UploadButton uploadButtonText={uploadButtonText} />
                </NoDataMessageWrapper>
            </ModuleBox>
  
            <p style={{textAlign: 'center'}}>or</p>
  
            <div style={{justifyContent: 'center', display: 'flex'}}>
                <StyledButton onClick={() => browserHistory.push('/create?type=' + browserHistory.location.pathname.slice(1))}>
                  Add Single User
                </StyledButton>
            </div>
        </PageWrapper>
      )
    }

    return (
      <WrapperDiv>
  
          <PageWrapper>
              <ThemeProvider theme={LightTheme}>
                  <TransferAccountListWithFilterWrapper transferAccountList={transferAccountList} />
              </ThemeProvider>
          </PageWrapper>
  
      </WrapperDiv>
    );
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(TransferAccountListPage);

const IconSVG = styled.img`
  width: 35px;
  padding: 1em 0 0.5em;
  display: flex;
`;

const NoDataMessageWrapper = styled.div`
  text-align: center;
  display: flex;
  justify-content: center;
  flex-direction: column;
  align-items: center;
`;
